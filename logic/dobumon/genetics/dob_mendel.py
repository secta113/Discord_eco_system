import random
from typing import Any, Dict, List

from logic.dobumon.genetics.traits.registry import TraitRegistry

from .dob_genetics_constants import GeneticConstants


class MendelEngine:
    """メンデルの法則に基づいた遺伝計算エンジン。

    対立遺伝子の交叉（Crossover）と表現型（Phenotype）の決定を担当します。
    """

    @staticmethod
    def crossover(p1_alleles: List[str], p2_alleles: List[str]) -> List[str]:
        """減数分裂と受精を行い、両親から1つずつランダムに対立遺伝子を継承します。"""

        def mutate_allele(allele: str) -> str:
            if allele in ["D", "r"]:
                return allele
            trait_obj = TraitRegistry.get(allele)
            return trait_obj.on_inherit_allele()

        return [mutate_allele(random.choice(p1_alleles)), mutate_allele(random.choice(p2_alleles))]

    @staticmethod
    def get_initial_genotype() -> Dict[str, List[str]]:
        """野生種または購入時の初期遺伝型を生成します。"""
        genotype = {}
        for key in GeneticConstants.TRAIT_GENES:
            genotype[key] = ["D", "r"]
        return genotype

    @staticmethod
    def resolve_traits(
        genotype: Dict[str, List[str]], genetics_meta: Dict[str, Any], gender: str = "M"
    ) -> List[str]:
        """遺伝型（Genotype）から実際に発現する特性名（Phenotype）を解決します。"""
        active_traits = []
        # 標準的な表現型名（"early", "hardy" など）のセットを作成
        standard_phenotypes = {
            phenotype
            for def_dict in GeneticConstants.TRAIT_GENES.values()
            for phenotype in (def_dict["D"], def_dict["r"])
        }

        # 突然変異（特殊）アレルとして有効なキーの集合
        # TraitRegistry に登録されている全特性から、標準表現型を除外したもの
        valid_mutation_alleles = {
            k for k in TraitRegistry.get_all_keys() if k not in standard_phenotypes
        }

        for locus_key, alleles in genotype.items():
            definition = GeneticConstants.TRAIT_GENES.get(locus_key)
            if not definition:
                continue

            # 1. 突然変異アレル（希少遺伝子）の検出
            # 複数の突然変異アレルがある場合（ヘテロ接合）、それら全てを発現させる
            locus_rare_traits = []
            for a in alleles:
                # 登録されている特殊アレルのみを突然変異として扱う
                if a in valid_mutation_alleles:
                    if a not in locus_rare_traits:
                        locus_rare_traits.append(a)

            # 変異が見つかればそれを発現特性とする（複数あり得る）
            if locus_rare_traits:
                active_traits.extend(locus_rare_traits)
            else:
                # 2. 通常の優劣遺伝判定 (Dがあれば優性表現型、なければ劣性表現型)
                if "D" in alleles:
                    active_traits.append(definition["D"])
                else:
                    active_traits.append(definition["r"])

        # 3. 血統に刻まれた「禁忌」因子の解決
        # 性別による発現制限 (Red=Male, Blue=Female)
        if gender == "M" and genetics_meta.get("has_forbidden_red"):
            active_traits.append("forbidden_red")
        if gender == "F" and genetics_meta.get("has_forbidden_blue"):
            active_traits.append("forbidden_blue")

        # 4. 特殊な解決順序の調整（オーバーライド系特性を末尾に移動）
        # 背反 (antinomy) など、他の特性の効果を打ち消すものは最後に適用される必要がある
        priority_overrides = ["antinomy", "anti_taboo"]
        for po in priority_overrides:
            if po in active_traits:
                active_traits.remove(po)
                active_traits.append(po)

        return active_traits
