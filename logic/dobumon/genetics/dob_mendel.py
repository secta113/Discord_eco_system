import random
from typing import Any, Dict, List

from logic.dobumon.core.dob_traits import TraitRegistry

from .dob_genetics_constants import GeneticConstants


class MendelEngine:
    """メンデルの法則に基づいた遺伝計算エンジン。

    対立遺伝子の交叉（Crossover）と表現型（Phenotype）の決定を担当します。
    """

    @staticmethod
    def crossover(p1_alleles: List[str], p2_alleles: List[str]) -> List[str]:
        """減数分裂と受精を行い、両親から1つずつランダムに対立遺伝子を継承します。"""

        def mutate_allele(allele: str) -> str:
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
        for key, alleles in genotype.items():
            definition = GeneticConstants.TRAIT_GENES.get(key)
            if not definition:
                continue

            # 1. 希少遺伝子（突然変異アレル）のチェック
            rare_trait = None
            generic_alleles = [
                "early",
                "late",
                "hardy",
                "frail",
                "stable",
                "burst",
                "aesthetic",
            ]

            # 特異的な優先順位を持つ特性をチェック
            priority_traits = ["antinomy", "singularity", "anti_taboo"]
            for pt in priority_traits:
                if pt in alleles:
                    rare_trait = pt
                    break

            if not rare_trait:
                for allele in alleles:
                    if (
                        allele in GeneticConstants.TRAIT_EFFECTS
                        and allele not in generic_alleles
                        and "forbidden" not in allele
                    ):
                        rare_trait = allele
                        break

            if rare_trait:
                active_traits.append(rare_trait)
            else:
                # 2. 通常の優劣遺伝判定 (DがあればDの表現型、なければr)
                if "D" in alleles:
                    active_traits.append(definition["D"])
                else:
                    active_traits.append(definition["r"])

        # 3. 血統に刻まれた「禁忌」因子の解決
        # 性別による発現制限 (Red=Male, Blue=Female)
        # 背反・禁断個体における「昇華」した発現は TabooLogic.resolve_taboo_transformation で後続処理される
        if gender == "M" and genetics_meta.get("has_forbidden_red"):
            active_traits.append("forbidden_red")
        if gender == "F" and genetics_meta.get("has_forbidden_blue"):
            active_traits.append("forbidden_blue")

        return active_traits
