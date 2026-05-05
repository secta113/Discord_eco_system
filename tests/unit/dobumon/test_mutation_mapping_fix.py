import random

import pytest

from logic.dobumon.core.dob_factory import DobumonFactory
from logic.dobumon.genetics.dob_genetics_constants import GeneticConstants


def test_forced_mutation_correct_locus():
    """
    DobumonFactory.create_new で force_mutation=True を指定した際、
    変異が正しい遺伝子座に配置されることを検証。
    """
    # 複数回試行して、各遺伝子座の変異が正しく配置されるか確認
    for _ in range(20):
        dobu = DobumonFactory.create_new(owner_id=1, name="TestMutation", force_mutation=True)

        genotype = dobu.genetics["genotype"]
        found_mutation = False

        for locus, alleles in genotype.items():
            for allele in alleles:
                if allele in GeneticConstants.TRAIT_EFFECTS and allele not in [
                    "early",
                    "late",
                    "hardy",
                    "frail",
                    "stable",
                    "burst",
                    "aesthetic",
                    "D",
                    "r",
                ]:
                    # このアレルがこの遺伝子座に属しているべきか確認
                    assert allele in GeneticConstants.MUTATION_GENE_POOL[locus], (
                        f"Mutation {allele} found in wrong locus {locus}"
                    )
                    found_mutation = True

        assert found_mutation, "No mutation found despite force_mutation=True"


def test_mutation_gene_pool_mapping():
    """
    MUTATION_GENE_POOL のマッピングがドキュメント通りであることを検証。
    """
    pool = GeneticConstants.MUTATION_GENE_POOL

    # Vitality
    assert "undead" in pool["vitality"]
    assert "crystalized" in pool["vitality"]
    assert "chimera" in pool["vitality"]
    assert "blue_blood" not in pool["vitality"]

    # Body
    assert "gold_horn" in pool["body"]
    assert "red_back" in pool["body"]
    assert "odd_eye" in pool["body"]
    assert "blue_blood" in pool["body"]
    assert "glass_blade" in pool["body"]
    assert "crystalized" not in pool["body"]


def test_migration_logic_simulation():
    """
    マイグレーションスクリプトのロジックが正しく動作するかシミュレーション。
    """
    # 以前のバグにより、undead が growth に入ってしまった個体を想定
    old_genotype = {
        "growth": ["undead", "r"],
        "vitality": ["hardy", "frail"],
        "potential": ["stable", "r"],
        "body": ["normal", "aesthetic"],
    }

    # 希少アレル抽出
    all_alleles = []
    for locus_alleles in old_genotype.values():
        for allele in locus_alleles:
            if allele in GeneticConstants.TRAIT_EFFECTS and allele not in [
                "early",
                "late",
                "hardy",
                "frail",
                "stable",
                "burst",
                "aesthetic",
                "D",
                "r",
            ]:
                all_alleles.append(allele)

    assert all_alleles == ["undead"]

    # 再配置
    new_genotype = {
        "growth": ["D", "r"],
        "vitality": ["D", "r"],
        "potential": ["D", "r"],
        "body": ["D", "r"],
    }
    for mutation in all_alleles:
        target_locus = None
        for locus, pool in GeneticConstants.MUTATION_GENE_POOL.items():
            if mutation in pool:
                target_locus = locus
                break
        if target_locus:
            new_genotype[target_locus] = [mutation, "r"]

    assert new_genotype["vitality"] == ["undead", "r"]
    assert new_genotype["growth"] == ["D", "r"]
