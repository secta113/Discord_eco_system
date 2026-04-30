import random
import uuid
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.core.dob_traits import TraitRegistry
from logic.dobumon.dob_shop.dob_shop_effect_manager import DobumonShopEffectManager
from logic.dobumon.genetics.dob_genetic_fixer import GeneticFixer
from logic.dobumon.genetics.dob_kinship import KinshipLogic
from logic.dobumon.genetics.dob_mendel import MendelEngine
from logic.dobumon.genetics.dob_taboo import TabooLogic


class IBreeder(ABC):
    """交配アルゴリズムのインターフェース。

    異なる配偶形態（Standard, Yuri, Bara）を統一的に扱うための基底抽象クラスです。
    """

    @abstractmethod
    def breed(self, parent1: Dobumon, parent2: Dobumon, child_name: str) -> Dobumon:
        pass


class BaseBreeder(IBreeder):
    """交配の共通ロジックを提供する基底クラス。"""

    def _parse_lineage(self, lineage: List[str]) -> Dict[str, tuple[int, float]]:
        return KinshipLogic.parse_lineage(lineage)

    def _calculate_coi(
        self,
        p1_id: str,
        p1_parsed: Dict[str, tuple[int, float]],
        p2_id: str,
        p2_parsed: Dict[str, tuple[int, float]],
    ) -> float:
        return KinshipLogic.calculate_coi(p1_id, p1_parsed, p2_id, p2_parsed)

    def _update_lineage_list(
        self,
        p1_id: str,
        p1_f: float,
        p1_parsed: Dict[str, tuple[int, float]],
        p2_id: str,
        p2_f: float,
        p2_parsed: Dict[str, tuple[int, float]],
        max_depth: int = 5,
    ) -> List[str]:
        return KinshipLogic.update_lineage_list(
            p1_id, p1_f, p1_parsed, p2_id, p2_f, p2_parsed, max_depth
        )

    def _calculate_potential(
        self, p1_iv: float, p2_iv: float, traits: List[str], iv_bonus: float = 0.0
    ) -> float:
        """両親の個体値(IV)と発現特性から、子のベースとなる個体値を算出します。"""
        avg = (p1_iv + p2_iv) / 2.0
        variation = random.uniform(0.9, 1.4)
        m_rate = 0.05

        for t in traits:
            trait_obj = TraitRegistry.get(t)
            m_rate *= getattr(trait_obj, "mutation_mod", 1.0)
            v_range = getattr(trait_obj, "variation_range", None)
            if v_range:
                # 振れ幅を特性で上書き (stable 等)
                variation = random.uniform(v_range[0], v_range[1])

        if random.random() < m_rate:
            variation += random.uniform(0.1, 0.3)

        if "supernova" in traits:
            variation = random.uniform(0.5, 2.5)
        elif "singularity" in traits:
            # 特異点仕様：両親の個体値の強い方を引き継ぎ、ブレをなくす
            avg = max(p1_iv, p2_iv)
            variation = 1.0

        return round(max(0.5, avg * variation + iv_bonus), 2)

    def _inherit_stat(
        self, p1_val: float, p2_val: float, iv: float, traits: List[str], stat_key: str
    ) -> float:
        """親のステータス実数値の平均に、IVと努力値(ランダム)、特性補正を掛けて実数値を算出します。"""
        base_val = (p1_val + p2_val) / 2.0
        inherited_effort = random.uniform(0, 5)
        final_val = (base_val * iv) + inherited_effort

        for t in traits:
            trait_obj = TraitRegistry.get(t)
            mod = getattr(trait_obj, f"{stat_key}_mod", 1.0)
            final_val *= mod

        return max(1, int(final_val))

    def _resolve_base_ivs(
        self, p1: Dobumon, p2: Dobumon, traits: List[str], is_yuri: bool, is_bara: bool
    ) -> Dict[str, float]:
        """両親からIVを引き継ぐ処理"""
        child_iv = {}
        # ショップアイテム効果の集計 (EffectManagerを利用)
        bonuses = DobumonShopEffectManager.get_breeding_bonuses(p1, p2)
        iv_bonus_base = bonuses["iv_bonus_base"]
        high_iv_bonus = bonuses["high_iv_bonus"]

        # 最も高いステータスの特定
        stats = ["hp", "atk", "defense", "eva", "spd"]
        highest_stat = stats[0]
        max_v = -1.0
        for s in stats:
            avg_p = (p1.iv.get(s, 1.0) + p2.iv.get(s, 1.0)) / 2.0
            if avg_p > max_v:
                max_v = avg_p
                highest_stat = s

        for stat in stats:
            p1_iv = p1.iv.get(stat, 1.0)
            p2_iv = p2.iv.get(stat, 1.0)

            current_bonus = iv_bonus_base
            if stat == highest_stat:
                current_bonus += high_iv_bonus

            iv = self._calculate_potential(p1_iv, p2_iv, traits, iv_bonus=current_bonus)

            if is_yuri:
                iv = round(iv * 1.15, 2)
            elif is_bara:
                iv = round(iv * 1.20, 2)

            child_iv[stat] = iv
        return child_iv

    def _resolve_final_stats(
        self, p1: Dobumon, p2: Dobumon, child_iv: Dict[str, float], traits: List[str], is_bara: bool
    ) -> Dict[str, int]:
        """IVをもとに最終実数値を計算"""
        child_stats = {}
        for s in ["hp", "atk", "defense", "eva", "spd"]:
            stat_val = self._inherit_stat(getattr(p1, s), getattr(p2, s), child_iv[s], traits, s)
            if is_bara:
                stat_val = int(stat_val * 1.2)
            child_stats[s] = stat_val
        return child_stats

    def _resolve_lifespan_and_illness(
        self, traits: List[str], inbreeding_f: float, is_bara: bool, forbidden_depth: int = 0
    ) -> tuple[float, float, bool, bool]:
        """寿命、病気率、延命可否、不妊状態を決定"""
        base_lifespan = float(random.randint(80, 120))
        # 1. 近親交配ペナルティ
        penalties = KinshipLogic.calculate_inbreeding_penalties(inbreeding_f)
        if inbreeding_f > 0:
            base_lifespan *= 1.0 - (penalties["lifespan_penalty_pct"] / 100)
        base_illness = 0.01 + (penalties["illness_gain_pct"] / 100)

        can_extend = True
        is_sterile = False

        # 2. 特性による寿命・病気率補正 (禁忌深度に応じた指数減衰を含む)
        for t in traits:
            trait_obj = TraitRegistry.get(t)
            l_mod = getattr(trait_obj, "lifespan_mod", 1.0)

            # 禁忌特性の場合、深度の数だけ重ね掛けする (指数関数的減少)
            # ただし「背反」または「禁断」がある場合はこの指数減衰（加速）を抑制するロジックは
            # Dobumon.consumption_mod で行われているが、ここでの初期寿命計算にも影響させるか。
            # 仕様上「寿命減少速度加速を無効」なので、初期寿命そのものの減衰は「背反」で防げると解釈。
            if t in ["forbidden_red", "forbidden_blue"] and forbidden_depth > 0:
                if "antinomy" not in traits and "the_forbidden" not in traits:
                    base_lifespan *= l_mod**forbidden_depth
                else:
                    # 加速無効化: 深度によらず1回分の補正のみにするか、あるいは完全に無効化(1.0)にするか。
                    # ここでは「加速」を無効化するので、ベースの減衰(l_mod)自体は残し、depth乗を止める。
                    base_lifespan *= l_mod
            else:
                base_lifespan *= l_mod

            base_illness *= getattr(trait_obj, "illness_mod", 1.0)

        # 3. 禁忌状態の個別フラグ処理
        if "forbidden_red" in traits:
            can_extend = False
            is_sterile = True
            base_illness += 0.15 if is_bara else 0.05

        if "forbidden_blue" in traits:
            can_extend = False
            base_illness += 0.03

        if "singularity" in traits:
            # 特異点：繁殖は可能だが、延命は不可
            is_sterile = False
            can_extend = False

        # --- 新特性による上書き ---
        if "antinomy" in traits:
            # 背反: 不妊を無効、延命を許可、寿命加速無効（上記計算で対応済み）
            is_sterile = False
            can_extend = True

        if "the_forbidden" in traits:
            # 禁断: 不妊、延命不可、寿命加速無効（上記計算で対応済み）
            # 禁断個体のバイタル（寿命）は 発生した寿命 × 禁忌深度 となる
            is_sterile = True
            can_extend = False
            base_lifespan = base_lifespan * max(1, forbidden_depth)

        illness_rate = max(0.0, base_illness)
        lifespan = max(1.0, float(int(base_lifespan)))
        return base_lifespan, base_illness, can_extend, is_sterile

    def _resolve_genotypes(self, p1: Dobumon, p2: Dobumon) -> Dict[str, List[str]]:
        """家系図からアレルペアを抽出し、Crossoverと真の突然変異を処理します。"""
        from logic.dobumon.genetics.dob_genetics_constants import GeneticConstants

        p1_geno = p1.genetics.get("genotype", MendelEngine.get_initial_genotype())
        p2_geno = p2.genetics.get("genotype", MendelEngine.get_initial_genotype())

        child_geno = {}
        for key in GeneticConstants.TRAIT_GENES:
            p1_alleles = p1_geno.get(key, ["D", "r"])
            p2_alleles = p2_geno.get(key, ["D", "r"])
            child_geno[key] = MendelEngine.crossover(p1_alleles, p2_alleles)

        # 突然変異の発生判定
        super_mutation_rate = 0.01
        for p in [p1, p2]:
            for t in p.traits:
                trait_obj = TraitRegistry.get(t)
                super_mutation_rate *= trait_obj.mutation_mod

        # ショップアイテム効果の集計
        bonuses = DobumonShopEffectManager.get_breeding_bonuses(p1, p2)
        super_mutation_rate += bonuses["mutation_chance_delta"]

        if random.random() < super_mutation_rate:
            slot = random.choice(list(GeneticConstants.MUTATION_GENE_POOL.keys()))
            mutation_allele = random.choice(GeneticConstants.MUTATION_GENE_POOL[slot])
            idx = random.randint(0, 1)

            child_geno[slot][idx] = mutation_allele

        return child_geno

    def _resolve_skills(self, p1: Dobumon, p2: Dobumon) -> List[Dict]:
        """親からスキルを継承"""
        parent_skills = (p1.skills or []) + (p2.skills or [])
        child_skills = []
        if parent_skills:
            unique_skills = []
            seen_names = set()
            for s in parent_skills:
                if s["name"] not in seen_names:
                    unique_skills.append(s)
                    seen_names.add(s["name"])
            num_to_inherit = min(len(unique_skills), random.randint(1, 2))
            child_skills = random.sample(unique_skills, num_to_inherit)
        return child_skills

    def breed_common(self, p1: Dobumon, p2: Dobumon, child_name: str, gender: str) -> Dobumon:
        """全配偶スタイルで共通して使用される継承フローを実行します。"""
        # 1. 家系図の解析と近親係数 (COI) の計算
        p1_parsed = self._parse_lineage(p1.lineage)
        p2_parsed = self._parse_lineage(p2.lineage)
        p1_f = p1.genetics.get("inbreeding_debt", 0.0)
        p2_f = p2.genetics.get("inbreeding_debt", 0.0)

        inbreeding_f = self._calculate_coi(p1.dobumon_id, p1_parsed, p2.dobumon_id, p2_parsed)
        child_lineage = self._update_lineage_list(
            p1.dobumon_id, p1_f, p1_parsed, p2.dobumon_id, p2_f, p2_parsed
        )

        # 2. 遺伝型アレルペアの継承と突然変異
        child_geno = self._resolve_genotypes(p1, p2)

        # 3. 表現型の解決（血統の禁忌を含む）
        genetics_meta = {}
        if p1.genetics.get("has_forbidden_red") or p2.genetics.get("has_forbidden_red"):
            genetics_meta["has_forbidden_red"] = True
        if p1.genetics.get("has_forbidden_blue") or p2.genetics.get("has_forbidden_blue"):
            genetics_meta["has_forbidden_blue"] = True

        # [NOTE] 誕生した個体が、自身の性別による「禁忌」因子発生と同時に「背反」へ変異（対禁忌遺伝子との結合）
        # できるようにするため、表現型解決の前に Bara/Yuri 判定とフラグ注入を行います。
        is_bara = p1.gender == "M" and p2.gender == "M"
        is_yuri = p1.gender == "F" and p2.gender == "F"
        if is_bara:
            genetics_meta["has_forbidden_red"] = True
        if is_yuri:
            genetics_meta["has_forbidden_blue"] = True

        # 性別を考慮した特性の解決
        traits = MendelEngine.resolve_traits(child_geno, genetics_meta, gender=gender)

        # 配偶スタイルの判定
        is_taboo = is_yuri or is_bara

        # 特殊配偶による特性の強制付与
        if is_yuri and "forbidden_blue" not in traits:
            traits.append("forbidden_blue")
        if is_bara and "forbidden_red" not in traits:
            traits.append("forbidden_red")

        # 禁忌深度の取得
        parent_depth_p1 = p1.genetics.get("forbidden_depth", 0)
        parent_depth_p2 = p2.genetics.get("forbidden_depth", 0)

        # ショップアイテム効果の集計
        bonuses = DobumonShopEffectManager.get_breeding_bonuses(p1, p2)
        shop_taboo_add = bonuses["taboo_depth_add"]

        # 3.5 禁忌変異の解決（対禁忌->背反 / 背反+禁忌->禁断）
        # ここで性別不一致因子の除去と、背反個体における「昇華」した特性発現が行われる
        traits, is_forbidden_trigger, genetics_meta = TabooLogic.resolve_taboo_transformation(
            traits, genetics_meta, gender=gender
        )

        # 3.6 伝承遺伝（Fixation）の適用: 特定形質が発現した場合、遺伝子座をホモ接合に固定する
        GeneticFixer.fixate_genotype(child_geno, traits)

        # 禁忌深度の真の計算（禁断時は加算ボーナス）
        child_depth = (
            TabooLogic.calculate_child_forbidden_depth(
                parent_depth_p1, parent_depth_p2, is_taboo, is_forbidden_trigger
            )
            + shop_taboo_add
        )

        # 4. 個体値(IV)の継承
        child_iv = self._resolve_base_ivs(p1, p2, traits, is_yuri, is_bara)

        # 5. ステータス実数値の決定
        child_stats = self._resolve_final_stats(p1, p2, child_iv, traits, is_bara)

        # 禁断発現時の初期ステータスボーナス (+ 深度 * 10)
        if is_forbidden_trigger:
            bonus = child_depth * 10
            for s in ["hp", "atk", "defense", "eva", "spd"]:
                child_stats[s] += bonus

        # 6. 特殊状態（不妊・寿命・病気率）の決定
        lifespan, illness_rate, can_extend, is_sterile = self._resolve_lifespan_and_illness(
            traits, inbreeding_f, is_bara, forbidden_depth=child_depth
        )

        # 7. 技の継承
        child_skills = self._resolve_skills(p1, p2)

        # 継承するメタ遺伝情報をパッキング（フィルタリング後の genetics_meta を使用）
        child_genetics = {
            "genotype": child_geno,
            "inbreeding_debt": inbreeding_f,
            "forbidden_depth": child_depth,
        }
        if genetics_meta.get("has_forbidden_red"):
            child_genetics["has_forbidden_red"] = True
        if genetics_meta.get("has_forbidden_blue"):
            child_genetics["has_forbidden_blue"] = True

        child = Dobumon(
            dobumon_id=str(uuid.uuid4()),
            owner_id=p1.owner_id,
            name=child_name,
            gender=gender,
            hp=child_stats["hp"],
            atk=child_stats["atk"],
            defense=child_stats["defense"],
            eva=child_stats["eva"],
            spd=child_stats["spd"],
            health=float(child_stats["hp"]),
            skills=child_skills,
            iv=child_iv,
            lifespan=lifespan,
            max_lifespan=lifespan,
            is_alive=True,
            attribute=random.choice(["fire", "water", "grass"]),
            affection=0,
            generation=max(p1.generation, p2.generation) + 1,
            genetics=child_genetics,
            lineage=child_lineage,
            traits=traits,
            is_sterile=is_sterile,
            illness_rate=illness_rate,
            can_extend_lifespan=can_extend,
        )
        return child


class StandardBreeder(BaseBreeder):
    """通常の交配。性別が異なる親同士。"""

    def breed(self, parent1: Dobumon, parent2: Dobumon, child_name: str) -> Dobumon:
        # 1. 性別の決定（禁忌による性別ロックと背反による克服）
        gender = self._decide_child_gender(parent1, parent2)

        # 2. 共通継承フローの実行
        child = self.breed_common(parent1, parent2, child_name, gender)
        return child

    def _decide_child_gender(self, p1: Dobumon, p2: Dobumon) -> str:
        """両親の禁忌状態に基づき、子の性別を決定します。"""
        # 禁忌特性のチェック
        has_red = "forbidden_red" in p1.traits or "forbidden_red" in p2.traits
        has_blue = "forbidden_blue" in p1.traits or "forbidden_blue" in p2.traits

        # 背反または禁断による「呪い」の克服チェック
        is_sublimated = any(t in p1.traits or t in p2.traits for t in ["antinomy", "the_forbidden"])

        if is_sublimated:
            # 呪い克服状態: 通常のショップ補正ロジックに従う
            bonuses = DobumonShopEffectManager.get_breeding_bonuses(p1, p2)
            bias_m = bonuses.get("gender_bias_m_chance", 0.0)
            bias_f = bonuses.get("gender_bias_f_chance", 0.0)

            if bias_m > 0 and bias_f == 0 and random.random() < bias_m:
                return "M"
            elif bias_f > 0 and bias_m == 0 and random.random() < bias_f:
                return "F"
            else:
                return random.choice(["M", "F"])
        else:
            # 呪い継続状態: 赤ならオス固定、青ならメス固定。両方（対立）なら 50/50
            if has_red and not has_blue:
                return "M"
            if has_blue and not has_red:
                return "F"

            # 通常（非禁忌）または対立時
            return random.choice(["M", "F"])


class YuriBreeder(BaseBreeder):
    """百合交配（メス×メス）。特定の血脈『青の禁忌』を発現します。"""

    def breed(self, parent1: Dobumon, parent2: Dobumon, child_name: str) -> Dobumon:
        # 百合配合は常にメス
        child = self.breed_common(parent1, parent2, child_name, "F")
        return child


class BaraBreeder(BaseBreeder):
    """薔薇交配（オス×オス）。特定の血脈『赤の禁忌』を発現します。"""

    def breed(self, parent1: Dobumon, parent2: Dobumon, child_name: str) -> Dobumon:
        # 薔薇配合は常にオス
        child = self.breed_common(parent1, parent2, child_name, "M")
        return child


class BreedingFactory:
    """両親の性別に基づいて、適切なBreederを選択するファクトリー。"""

    @staticmethod
    def get_breeder(p1: Dobumon, p2: Dobumon) -> IBreeder:
        if p1.gender == "F" and p2.gender == "F":
            return YuriBreeder()
        elif p1.gender == "M" and p2.gender == "M":
            return BaraBreeder()
        return StandardBreeder()
