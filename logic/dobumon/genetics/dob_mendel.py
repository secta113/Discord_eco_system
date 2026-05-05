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
        all_mutation_keys = TraitRegistry.get_all_keys()
        
        # 標準的なアレルの表現型名（early, late 等）のリストを取得
        # これらは対立遺伝子として genotype に直接入ることは通常ないが、
        # 万が一入っていた場合に「突然変異」として誤検知されないように除外する。
        standard_phenotype_names = []
        for def_dict in GeneticConstants.TRAIT_GENES.values():
            standard_phenotype_names.extend([def_dict["D"], def_dict["r"]])

        for locus_key, alleles in genotype.items():
            definition = GeneticConstants.TRAIT_GENES.get(locus_key)
            if not definition:
                continue

            # 1. 突然変異アレル（希少遺伝子）の検出
            # 優先順位が高い順にチェック
            priority_mutations = ["antinomy", "singularity", "anti_taboo"]
            rare_trait = None
            
            # まず優先度の高い変異があるかチェック
            for pm in priority_mutations:
                if pm in alleles:
                    rare_trait = pm
                    break

            # 次にそれ以外の突然変異をチェック
            if not rare_trait:
                for a in alleles:
                    # アレル名が TraitRegistry に存在し、かつ標準的なアレル(D, r)や
                    # 標準的な表現型名、禁忌形質（これらは後続処理で付与）でない場合
                    if (
                        a in all_mutation_keys
                        and a not in ["D", "r"]
                        and a not in standard_phenotype_names
                        and "forbidden" not in a
                    ):
                        rare_trait = a
                        break

            # 変異が見つかればそれを発現特性とする
            if rare_trait:
                active_traits.append(rare_trait)
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

        return active_traits
