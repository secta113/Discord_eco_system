import pytest

from logic.dobumon.genetics.dob_genetics_constants import GeneticConstants
from logic.dobumon.genetics.dob_mendel import MendelEngine
from logic.dobumon.genetics.traits.registry import TraitRegistry


def test_all_special_traits_resolved():
    """全ての特殊形質（突然変異等）がアレルに存在する場合に正しく判定・発現するかテストする"""
    all_keys = TraitRegistry.get_all_keys()

    # 標準的な表現型名を取得
    standard_phenotype_names = []
    for def_dict in GeneticConstants.TRAIT_GENES.values():
        standard_phenotype_names.extend([def_dict["D"], def_dict["r"]])

    # 禁忌系など後続処理で付与される特殊なもの
    # ただし "the_forbidden" がアレルとして存在し得る場合、発現するかどうかをチェックする
    special_traits = [k for k in all_keys if k not in standard_phenotype_names]

    failed_traits = []

    for trait in special_traits:
        # 該当の特性をアレルに持つ遺伝子型を作成
        genotype = {
            "potential": [trait, "r"]  # 便宜上 potential locus を使用
        }

        # 禁忌(forbidden_red, forbidden_blue)は meta 情報で付与されるため
        # アレルとしては直接付与されない想定だが、the_forbiddenは？

        resolved_traits = MendelEngine.resolve_traits(genotype, genetics_meta={}, gender="M")

        # forbidden_red, forbidden_blue は血統メタ情報から解決されるのでアレルからは発現しない
        if trait in ["forbidden_red", "forbidden_blue"]:
            continue

        if trait not in resolved_traits:
            failed_traits.append(trait)

    assert not failed_traits, f"These special traits were not correctly resolved: {failed_traits}"
