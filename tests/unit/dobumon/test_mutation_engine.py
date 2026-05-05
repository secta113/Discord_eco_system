import pytest

from logic.dobumon.genetics.dob_genetics_constants import GeneticConstants
from logic.dobumon.genetics.dob_mutation import MutationEngine


def test_mutation_engine_random_generation():
    """ランダムな突然変異が正しく選択されるか検証"""
    for _ in range(100):
        slot, allele = MutationEngine.generate_random_mutation()
        assert slot in GeneticConstants.MUTATION_GENE_POOL
        assert allele in GeneticConstants.MUTATION_GENE_POOL[slot]


def test_apply_mutation_normal():
    """通常の突然変異が片方の座に適用されるか検証"""
    genotype = {
        "growth": ["D", "r"],
        "vitality": ["D", "r"],
        "potential": ["D", "r"],
        "body": ["D", "r"],
    }
    # undead は通常変異 (vitality)
    MutationEngine.apply_mutation(genotype, allele="undead")

    # 片方が undead, もう片方が D or r であること
    assert "undead" in genotype["vitality"]
    assert "D" in genotype["vitality"] or "r" in genotype["vitality"]
    assert genotype["vitality"] != ["undead", "undead"]


def test_apply_mutation_fixated():
    """強力な変異（singularity等）が両方の座に適用（固定）されるか検証"""
    genotype = {
        "growth": ["D", "r"],
        "vitality": ["D", "r"],
        "potential": ["D", "r"],
        "body": ["D", "r"],
    }
    # singularity は固定対象 (potential)
    MutationEngine.apply_mutation(genotype, allele="singularity")

    # 両方が singularity になっていること
    assert genotype["potential"] == ["singularity", "singularity"]


def test_fixate_genotype():
    """既存の特性リストに基づく固定処理を検証"""
    genotype = {"potential": ["singularity", "r"]}
    # traits に singularity が含まれる場合、固定されるべき
    MutationEngine.fixate_genotype(genotype, ["singularity", "hardy"])
    assert genotype["potential"] == ["singularity", "singularity"]


def test_apply_mutation_no_slot_inference():
    """スロット未指定時にアレルからスロットを推論できるか検証"""
    genotype = {"body": ["D", "r"]}
    # gold_horn は body
    MutationEngine.apply_mutation(genotype, allele="gold_horn")
    assert "gold_horn" in genotype["body"]


def test_apply_mutation_unknown_allele():
    """未知のアレルが指定された場合にエラーが発生するか検証"""
    from logic.dobumon.core.dob_exceptions import DobumonGeneticsError

    genotype = {"growth": ["D", "r"]}
    with pytest.raises(DobumonGeneticsError, match="Unknown mutation allele"):
        MutationEngine.apply_mutation(genotype, allele="non_existent_mutation")
