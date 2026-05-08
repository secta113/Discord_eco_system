import json
import os
import sqlite3
import sys
from collections import Counter
from typing import Any, Dict, List, Tuple

# プロジェクトルートをパスに追加
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)

from core.handlers.storage import DatabaseConfig
from logic.dobumon.core.dob_factory import DobumonFactory
from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.genetics.dob_genetics_constants import GeneticConstants
from logic.dobumon.genetics.dob_mendel import MendelEngine
from logic.dobumon.genetics.dob_mutation import MutationEngine
from logic.dobumon.genetics.traits.registry import TraitRegistry


def _extract_mutation_alleles(
    genotype: Dict[str, List[str]], all_mutation_keys: List[str]
) -> List[str]:
    """ゲノタイプから希少アレルのみを抽出する"""
    all_alleles = []
    exclude_list = ["early", "late", "hardy", "frail", "stable", "burst", "aesthetic", "D", "r"]
    for _locus, alleles in genotype.items():
        for a in alleles:
            if a in all_mutation_keys and a not in exclude_list and "forbidden" not in a:
                all_alleles.append(a)
    return all_alleles


def _group_mutations_by_locus(all_alleles: List[str]) -> Dict[str, List[str]]:
    """希少アレルを本来あるべき遺伝子座ごとにグループ化する"""
    locus_groups = {}
    for allele in all_alleles:
        target_locus = None
        for locus, pool in GeneticConstants.MUTATION_GENE_POOL.items():
            if allele in pool:
                target_locus = locus
                break
        if target_locus:
            locus_groups.setdefault(target_locus, []).append(allele)
    return locus_groups


def _reconstruct_genotype(
    locus_groups: Dict[str, List[str]],
    base_alleles_map: Dict[str, List[str]],
    is_active: bool,
    owner_info: Tuple[str, str, str],
    priority_map: Dict[str, int],
) -> Tuple[Dict[str, List[str]], List[Dict[str, Any]]]:
    """優先順位とベースアレルを考慮してゲノタイプを再構成する"""
    new_genotype = {}
    lost_alleles = []
    owner_id, name, dobumon_id = owner_info

    for locus in ["growth", "vitality", "potential", "body"]:
        mutations = locus_groups.get(locus, [])

        if mutations:
            mutations.sort(key=lambda x: priority_map.get(x, 99))
            counts = Counter(mutations)
            primary = mutations[0]
            is_fixed = (primary in MutationEngine.FIX_RULES) or (counts[primary] >= 2)

            if is_fixed:
                new_genotype[locus] = [primary, primary]
                if is_active:
                    for m in mutations:
                        if m != primary:
                            lost_alleles.append(
                                {
                                    "owner": owner_id,
                                    "dobumon": name,
                                    "dobumon_id": dobumon_id,
                                    "locus": locus,
                                    "lost_allele": m,
                                    "reason": f"Fixed by {primary}",
                                }
                            )
            else:
                secondary = mutations[1] if len(mutations) > 1 else "D"
                new_genotype[locus] = [primary, secondary]
                if is_active and len(mutations) > 2:
                    for m in mutations[2:]:
                        lost_alleles.append(
                            {
                                "owner": owner_id,
                                "dobumon": name,
                                "dobumon_id": dobumon_id,
                                "locus": locus,
                                "lost_allele": m,
                                "reason": "Locus slot limit (max 2)",
                            }
                        )
        else:
            res = base_alleles_map[locus]
            if len(res) == 2:
                new_genotype[locus] = res
            elif len(res) == 1:
                new_genotype[locus] = [res[0], "D"]
            else:
                new_genotype[locus] = ["D", "r"]

    return new_genotype, lost_alleles


def migrate(dry_run: bool = True):
    """遺伝子座のズレを修正し、特性・ステータスの不整合を解消するマイグレーション"""
    all_mutation_keys = TraitRegistry.get_all_keys()
    db_path = DatabaseConfig.get_db_path()

    print(f"Target database: {db_path}")
    if dry_run:
        print("=== DRY RUN MODE: No changes will be saved to the database ===")

    if not os.path.exists(db_path):
        print("Database file not found. Skipping migration.")
        return

    conn = sqlite3.connect(
        f"file:{db_path}?mode=ro" if dry_run else db_path, uri=True if dry_run else False
    )
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM dobumons")
    rows = cursor.fetchall()
    print(f"Found {len(rows)} dobumons to check.")

    updated_count = 0
    lost_alleles_report = []
    alive_logs, other_logs = [], []
    priority_map = {"antinomy": 0, "singularity": 1, "anti_taboo": 2}

    for row in rows:
        try:
            genetics = json.loads(row["genetics"])
            genotype = genetics.get("genotype")
            if not genotype:
                continue

            base_alleles_map = {
                locus: [a for a in alleles if a in ["D", "r"]]
                for locus, alleles in genotype.items()
            }

            flat_alleles = []
            for alleles in genotype.values():
                flat_alleles.extend(alleles)

            all_alleles = []
            exclude_list = [
                "early",
                "late",
                "hardy",
                "frail",
                "stable",
                "burst",
                "aesthetic",
                "D",
                "r",
            ]
            for a in flat_alleles:
                if a in all_mutation_keys and a not in exclude_list and "forbidden" not in a:
                    all_alleles.append(a)

            locus_groups = _group_mutations_by_locus(all_alleles)
            owner_info = (row["owner_id"], row["name"], row["dobumon_id"])
            is_active = row["is_alive"] == 1 and row["is_sold"] == 0

            new_genotype, lost = _reconstruct_genotype(
                locus_groups, base_alleles_map, is_active, owner_info, priority_map
            )
            lost_alleles_report.extend(lost)
            new_traits = MendelEngine.resolve_traits(new_genotype, genetics, gender=row["gender"])

            # 既存データとの比較
            old_traits = json.loads(row["traits"]) if row["traits"] else []
            traits_changed = set(old_traits) != set(new_traits) or old_traits != new_traits
            genotype_changed = new_genotype != genotype

            # ステータス補正のシミュレーション
            temp_dobu = Dobumon(
                dobumon_id=row["dobumon_id"],
                owner_id=row["owner_id"],
                name=row["name"],
                gender=row["gender"],
                hp=row["hp"],
                atk=row["atk"],
                defense=row["defense"],
                eva=row["eva"],
                spd=row["spd"],
                health=row["health"],
                lifespan=row["lifespan"],
                max_lifespan=row["max_lifespan"],
                traits=new_traits,
                genetics=genetics,
            )
            temp_dobu.illness_rate = row["illness_rate"]
            temp_dobu.is_sterile = row["is_sterile"] == 1

            # --- 寿命補正の特殊処理 ---
            if "undead" in new_traits and temp_dobu.max_lifespan < 200:
                temp_dobu.lifespan *= 5.0
                temp_dobu.max_lifespan *= 5.0

            # 一般的な特性補正を適用
            MutationEngine.apply_phenotype_modifiers(temp_dobu)

            if is_active:
                temp_dobu.health = temp_dobu.hp

            stats_changed = (
                abs(temp_dobu.lifespan - row["lifespan"]) > 0.1
                or abs(temp_dobu.max_lifespan - row["max_lifespan"]) > 0.1
                or temp_dobu.hp != row["hp"]
                or temp_dobu.health != row["health"]
                or temp_dobu.is_sterile != (row["is_sterile"] == 1)
            )

            if genotype_changed or traits_changed or stats_changed:
                updated_count += 1
                status = "ALIVE" if row["is_alive"] == 1 else "DEAD/SOLD"
                entry = f"[{status}] {row['name']} ({row['dobumon_id']})\n"
                if genotype_changed:
                    entry += f"  Genotype: {genotype} -> {new_genotype}\n"
                if traits_changed:
                    entry += f"  Traits: {old_traits} -> {new_traits}\n"
                if stats_changed:
                    entry += f"  Lifespan: {row['lifespan']} -> {temp_dobu.lifespan}\n"
                    entry += f"  HP/Health: {row['hp']}/{row['health']} -> {temp_dobu.hp}/{temp_dobu.health}\n"
                    entry += f"  Sterile: {bool(row['is_sterile'])} -> {temp_dobu.is_sterile}\n"
                entry += "\n"

                if row["is_alive"] == 1:
                    alive_logs.append(entry)
                else:
                    other_logs.append(entry)

                if not dry_run:
                    genetics["genotype"] = new_genotype
                    genetics["v2_2_migrated"] = True
                    cursor.execute(
                        """UPDATE dobumons SET
                            genetics = ?, traits = ?,
                            hp = ?, atk = ?, defense = ?, eva = ?, spd = ?, health = ?,
                            lifespan = ?, max_lifespan = ?, is_sterile = ?, illness_rate = ?
                           WHERE dobumon_id = ?""",
                        (
                            json.dumps(genetics),
                            json.dumps(new_traits),
                            temp_dobu.hp,
                            temp_dobu.atk,
                            temp_dobu.defense,
                            temp_dobu.eva,
                            temp_dobu.spd,
                            temp_dobu.health,
                            temp_dobu.lifespan,
                            temp_dobu.max_lifespan,
                            1 if temp_dobu.is_sterile else 0,
                            temp_dobu.illness_rate,
                            row["dobumon_id"],
                        ),
                    )
        except Exception as e:
            # 静かにログに書き込むだけでコンソールには出さない（エンコードエラー回避）
            other_logs.append(f"Error processing {row['dobumon_id']}: {e}\n")

    with open("fix_log.txt", "w", encoding="utf-8") as f:
        f.write(f"=== DOBUMON MIGRATION FIX LOG ===\nUpdated: {updated_count}\n\n")
        f.write("SECTION 1: ACTIVE UPDATES\n")
        f.writelines(alive_logs)
        f.write("\nSECTION 2: OTHERS\n")
        f.writelines(other_logs)

    if not dry_run and updated_count > 0:
        conn.commit()
    conn.close()
    print(f"Migration finished. Updated: {updated_count}")


if __name__ == "__main__":
    migrate(dry_run="--apply" not in sys.argv)
