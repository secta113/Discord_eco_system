import json
import os
import sqlite3
import sys

# プロジェクトルートをパスに追加（インポートを可能にするため）
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.handlers.storage import DatabaseConfig
from logic.dobumon.genetics.dob_genetics_constants import GeneticConstants
from logic.dobumon.genetics.dob_mendel import MendelEngine
from logic.dobumon.genetics.dob_mutation import MutationEngine


def migrate():
    db_path = DatabaseConfig.get_db_path()
    print(f"Starting migration on database: {db_path}")

    if not os.path.exists(db_path):
        print("Database file not found. Skipping migration.")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 全ての怒武者データを取得
    cursor.execute("SELECT dobumon_id, genetics, name FROM dobumons")
    rows = cursor.fetchall()
    print(f"Found {len(rows)} dobumons to check.")

    updated_count = 0
    for row in rows:
        dobumon_id = row["dobumon_id"]
        name = row["name"]
        try:
            genetics = json.loads(row["genetics"])
        except Exception:
            continue

        genotype = genetics.get("genotype")
        if not genotype:
            continue

        # 1. 現在の全ての希少アレル（突然変異）を抽出
        all_alleles = []
        for locus_alleles in genotype.values():
            for allele in locus_alleles:
                if (
                    allele in GeneticConstants.TRAIT_EFFECTS
                    and allele
                    not in [
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
                    and "forbidden" not in allele
                ):
                    all_alleles.append(allele)

        if not all_alleles:
            continue

        # 2. 遺伝子座をリセット
        new_genotype = {
            "growth": ["D", "r"],
            "vitality": ["D", "r"],
            "potential": ["D", "r"],
            "body": ["D", "r"],
        }

        # 3. 希少アレルを正しい位置に再配置
        mutation_counts = {}
        for a in all_alleles:
            mutation_counts[a] = mutation_counts.get(a, 0) + 1

        for mutation, count in mutation_counts.items():
            # 正しい遺伝子座を特定
            target_locus = None
            for locus, pool in GeneticConstants.MUTATION_GENE_POOL.items():
                if mutation in pool:
                    target_locus = locus
                    break

            if target_locus:
                # MutationEngine の固定ルールを適用
                if mutation in MutationEngine.FIX_RULES:
                    new_genotype[target_locus] = [mutation, mutation]
                elif count >= 2:
                    new_genotype[target_locus] = [mutation, mutation]
                else:
                    new_genotype[target_locus] = [mutation, "r"]

        # 4. 表現型（traits）の再計算
        new_traits = MendelEngine.resolve_traits(new_genotype, genetics)

        if new_genotype != genotype:
            genetics["genotype"] = new_genotype
            # データベースを更新
            cursor.execute(
                "UPDATE dobumons SET genetics = ?, traits = ? WHERE dobumon_id = ?",
                (json.dumps(genetics), json.dumps(new_traits), dobumon_id),
            )
            updated_count += 1
            print(f"Updated {name} ({dobumon_id}): Loci corrected and fixated.")

    conn.commit()
    conn.close()
    print(f"Migration completed. Total {updated_count} dobumons updated.")


if __name__ == "__main__":
    migrate()
