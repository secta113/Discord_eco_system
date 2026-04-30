import os
import uuid

import pytest

from core.handlers import sql_handler
from core.handlers.storage import SQLiteDobumonRepository
from logic.dobumon.core.dob_manager import DobumonManager
from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.genetics.dob_breeders import BreedingFactory
from logic.dobumon.genetics.dob_genetics_constants import GeneticConstants
from logic.dobumon.genetics.dob_mendel import MendelEngine


def test_initial_genotype():
    """第1世代の遺伝子生成テスト"""
    genotype = MendelEngine.get_initial_genotype()
    assert "growth" in genotype
    assert "vitality" in genotype
    assert "potential" in genotype
    # 野生種はヘテロ接合体のはず
    assert genotype["growth"] == ["D", "r"]


def test_mendelian_crossover_statistics():
    """メンデルの分離の法則（3:1）の統計的検証"""
    # 両親ともヘテロ接合体 [D, r] の場合
    p1_alleles = ["D", "r"]
    p2_alleles = ["D", "r"]

    trials = 1000
    results = []
    for _ in range(trials):
        child = MendelEngine.crossover(p1_alleles, p2_alleles)
        # 優性形質が出るのは DD, Dr, rD (すべて 'D' を含む)
        has_dominant = "D" in child
        results.append(has_dominant)

    dominant_count = sum(results)
    ratio = dominant_count / trials
    # 期待値は 0.75 (3/1)。許容範囲 0.70 ~ 0.80
    assert 0.70 <= ratio <= 0.80


def test_lineage_and_inbreeding(tmp_path):
    """家系図と近親交配の影響テスト"""
    db_path = str(tmp_path / "test_genetics.db")
    sql_handler.init_db(db_path)
    repo = SQLiteDobumonRepository(db_path)
    manager = DobumonManager(repo)

    # 共通の祖先 A
    ancestor_a = manager.create_dobumon(owner_id=1, name="始祖A")
    manager.save_dobumon(ancestor_a)

    # 子 B, C (兄妹)
    p_male = manager.create_dobumon(owner_id=1, name="父")
    p_male.gender = "M"
    p_male.lifespan = 80.0

    p_male.max_lifespan = 100.0
    manager.save_dobumon(p_male)

    p_female = manager.create_dobumon(owner_id=1, name="母")
    p_female.gender = "F"
    p_female.lifespan = 80.0

    p_female.max_lifespan = 100.0
    manager.save_dobumon(p_female)

    # 兄妹を作る
    res_b = manager.breed_dobumon(p_male.dobumon_id, p_female.dobumon_id, "兄B")
    child_b = res_b["child"]
    child_b.gender = "M"
    child_b.lifespan = 80.0

    child_b.max_lifespan = 100.0
    manager.save_dobumon(child_b)

    res_c = manager.breed_dobumon(p_male.dobumon_id, p_female.dobumon_id, "妹C")
    child_c = res_c["child"]
    child_c.gender = "F"
    child_c.lifespan = 80.0

    child_c.max_lifespan = 100.0
    manager.save_dobumon(child_c)

    # 兄妹交配 (Inbreeding)
    res_inbred = manager.breed_dobumon(child_b.dobumon_id, child_c.dobumon_id, "近親の子")
    inbred = res_inbred["child"]

    # 共同先祖(p_male, p_female)による近親係数が 0.25 になるはず
    assert inbred.genetics["inbreeding_debt"] == 0.25
    # 近親デバフにより病気率が上がっているはず (基本0.01 + 2 * 0.05 = 0.11)
    # 特性で0.5倍などになる可能性があるため、0.05以上を検証
    assert inbred.illness_rate > 0.05
    # 寿命も減衰しているはず
    assert inbred.lifespan < 130


def test_trait_resolution():
    """表現型の解決テスト"""
    # 劣性ホモ接合体 [r, r]
    genotype = {"growth": ["r", "r"], "vitality": ["D", "r"]}
    traits = MendelEngine.resolve_traits(genotype, {})

    # growth は late (r) になるはず
    assert "late" in traits
    # vitality は hardy (D) になるはず
    assert "hardy" in traits


def test_rare_mutation_spawning():
    """希少突然変異の発現と永続遺伝のテスト"""
    p1 = Dobumon(
        dobumon_id="p1",
        owner_id=1,
        name="P1",
        gender="M",
        hp=100,
        atk=100,
        defense=100,
        eva=100,
        spd=100,
    )
    p2 = Dobumon(
        dobumon_id="p2",
        owner_id=1,
        name="P2",
        gender="F",
        hp=100,
        atk=100,
        defense=100,
        eva=100,
        spd=100,
    )

    # 強制的に100%突然変異が起きる環境をシミュレート（内部ロジックをモックするか、多数回試行）
    import random

    random.seed(42)  # 特定のシードで突然変異を引くように調整（あるいはループで回す）

    found = False
    for _ in range(1000):
        breeder = BreedingFactory.get_breeder(p1, p2)
        child = breeder.breed(p1, p2, "Mutant")
        # いずれかの希少形質が出たか

        all_mutations = sum(GeneticConstants.MUTATION_GENE_POOL.values(), [])
        if any(t in all_mutations for t in child.traits):
            found = True
            # 次代への継承テスト
            child.gender = "M"
            p3 = Dobumon(
                dobumon_id="p3",
                owner_id=1,
                name="P3",
                gender="F",
                hp=100,
                atk=100,
                defense=100,
                eva=100,
                spd=100,
            )
            breeder2 = BreedingFactory.get_breeder(child, p3)
            grandchild = breeder2.breed(child, p3, "Grandchild")

            # メンデルの法則により50%の確率で継承されるはず
            # 10体作れば、ほぼ確実に1体以上は引き継ぐ
            inherited = False
            for _ in range(10):
                grandchild = breeder2.breed(child, p3, f"Grandchild-{_}")
                if any(t in all_mutations for t in grandchild.traits):
                    inherited = True
                    break
                elif "singularity" in child.traits and "stable" in grandchild.traits:
                    # 特異点が劣化して安定として遺伝した場合は成功とみなす
                    inherited = True
                    break
            assert inherited, "突然変異形質が子孫に全く継承されませんでした。"
            break

    assert found, "200回の試行で一度も突然変異が発生しませんでした。"


def test_iv_inheritance():
    """ポテンシャルの継承テスト"""
    p1 = Dobumon(
        dobumon_id="1",
        owner_id=1,
        name="P1",
        gender="M",
        hp=100,
        atk=100,
        defense=100,
        eva=100,
        spd=100,
        iv={"hp": 1.5, "atk": 1.5, "defense": 1.5, "eva": 1.5, "spd": 1.5},
    )
    p2 = Dobumon(
        dobumon_id="2",
        owner_id=1,
        name="P2",
        gender="F",
        hp=100,
        atk=100,
        defense=100,
        eva=100,
        spd=100,
        iv={"hp": 1.5, "atk": 1.5, "defense": 1.5, "eva": 1.5, "spd": 1.5},
    )

    breeder = BreedingFactory.get_breeder(p1, p2)
    # 大量の試行でも、概ね親のIV(1.5)に近い値になるはず
    child = breeder.breed(p1, p2, "Child")
    for _stat, val in child.iv.items():
        # 1.5 の 0.9 ~ 1.4 程度 = 1.35 ~ 2.1
        assert 1.3 <= val <= 2.2
