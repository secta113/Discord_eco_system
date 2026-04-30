from unittest.mock import MagicMock

import pytest

from core.handlers.storage import IDobumonRepository
from logic.dobumon.core.dob_manager import DobumonManager
from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.core.dob_traits import (
    ParasiticTrait,
    SingularityTrait,
    TraitRegistry,
    UndeadTrait,
    UnlimitedTrait,
)
from logic.dobumon.genetics.dob_breeders import BreedingFactory
from logic.dobumon.genetics.dob_mendel import MendelEngine
from logic.dobumon.training import TrainingEngine


@pytest.fixture
def mock_storage():
    return MagicMock(spec=IDobumonRepository)


@pytest.fixture
def manager(mock_storage):
    return DobumonManager(mock_storage)


@pytest.fixture
def sample_dobu():
    return Dobumon(
        dobumon_id="test-id",
        owner_id=1,
        name="TestDobu",
        gender="M",
        hp=100.0,
        atk=50.0,
        defense=40.0,
        eva=10.0,
        spd=15.0,
        health=100.0,
        traits=[],
    )


class TestSpecialClasses:
    """特殊クラス（ロジックを持つ特性）のテスト"""

    def test_undead_trait_prevents_death(self, manager, sample_dobu):
        """不死（undead）特性が戦闘での死亡を無効化することを確認"""
        sample_dobu.traits = ["undead"]
        sample_dobu.health = 0.0

        # 戦闘での死亡シナリオ
        result = manager.handle_death(sample_dobu, "Wild Battle Death")

        assert result is False  # 死亡が回避された
        assert sample_dobu.is_alive is True
        assert sample_dobu.health >= 1.0

    def test_unlimited_trait_ignores_growth_decay(self):
        """無限（unlimited）特性が成長減衰を無視することを確認"""
        trait = TraitRegistry.get("unlimited")
        assert isinstance(trait, UnlimitedTrait)

        # 通常、ステータス1000では減衰が発生する (1 / (1 + (1000/500)^2) = 0.2)
        base_decay = TrainingEngine._get_growth_multiplier(1000.0)
        assert base_decay < 0.5

        # UnlimitedTraitは1.0以上を保証する
        unlimited_multiplier = trait.on_growth_multiplier(base_decay)
        assert unlimited_multiplier >= 1.0

    def test_parasitic_trait_penalizes_training(self):
        """捕食（parasitic）特性がトレーニング成長を抑制することを確認"""
        trait = TraitRegistry.get("parasitic")
        assert isinstance(trait, ParasiticTrait)

        base_multiplier = 1.0
        parasitic_multiplier = trait.on_growth_multiplier(base_multiplier)
        assert parasitic_multiplier == 0.1

    def test_parasitic_trait_boosts_rewards(self):
        """捕食（parasitic）特性が戦闘報酬を増加させることを確認"""
        trait = TraitRegistry.get("parasitic")
        exp, pts = trait.on_combat_reward(100.0, 1000)
        assert exp == 300.0
        assert pts == 3000

    def test_singularity_trait_is_permanently_inherited(self):
        """特異点（singularity）特性が遺伝時に劣化せず、そのまま継承されることを確認"""
        # 親のアレルに singularity がある場合
        p1_alleles = ["singularity", "singularity"]
        p2_alleles = ["singularity", "singularity"]

        # crossoverを実行
        child_alleles = MendelEngine.crossover(p1_alleles, p2_alleles)

        # 子のアレルも singularity のまま維持されているはず
        assert "singularity" in child_alleles
        assert "D" not in child_alleles


class TestConceptualMutations:
    """概念的突然変異（ステータス補正中心）のテスト"""

    def test_crystalized_stats(self):
        """結晶化（crystalized）のステータス補正確認"""
        trait = TraitRegistry.get("crystalized")
        assert trait.get_stat_multiplier("def") == 2.0
        assert trait.get_stat_multiplier("hp") == 0.5
        assert trait.get_stat_multiplier("illness") == 0.0

    def test_chimera_stats(self):
        """合成獣（chimera）のステータス補正確認"""
        trait = TraitRegistry.get("chimera")
        assert trait.get_stat_multiplier("hp") == 2.5
        assert trait.get_stat_multiplier("illness") == 3.0

    def test_glass_blade_stats(self):
        """硝子の刃（glass_blade）のステータス補正確認"""
        trait = TraitRegistry.get("glass_blade")
        assert trait.get_stat_multiplier("atk") == 2.5
        assert trait.get_stat_multiplier("spd") == 2.5
        assert trait.get_stat_multiplier("hp") == 0.5
        assert trait.get_stat_multiplier("def") == 0.5

    def test_supernova_mutation_boost(self):
        """超新星（supernova）の突然変異率補正確認"""
        trait = TraitRegistry.get("supernova")
        assert trait.mutation_mod == 5.0
        assert trait.variation_range == (0.5, 2.5)


class TestRareMutations:
    """希少突然変異のテスト"""

    def test_gold_horn_rewards(self):
        """金角（gold_horn）の報酬補正確認"""
        trait = TraitRegistry.get("gold_horn")
        assert trait.reward_mod == 1.1
        assert trait.get_stat_multiplier("def") == 1.2

    def test_rare_stat_mods(self):
        """他の希少形質のステータス補正確認"""
        assert TraitRegistry.get("red_back").get_stat_multiplier("atk") == 1.3
        assert TraitRegistry.get("odd_eye").get_stat_multiplier("eva") == 1.3
        assert TraitRegistry.get("blue_blood").get_stat_multiplier("hp") == 1.3
        assert TraitRegistry.get("blue_blood").get_stat_multiplier("illness") == 0.5


class TestIntegrationBreeding:
    """配布・継承のインテグレーションテスト"""

    def test_breeding_with_special_traits(self, manager):
        """特殊形質を持つ親からの継承フロー（特異点維持を含む）"""
        p1 = manager.create_dobumon(1, "Father")
        p2 = manager.create_dobumon(1, "Mother")

        # 特異点（singularity）を potential locus に付与
        p1.genetics["genotype"]["potential"] = ["singularity", "singularity"]
        p1.traits = ["singularity"]

        breeder = BreedingFactory.get_breeder(p1, p2)
        child = breeder.breed(p1, p2, "Child")

        # 特異点が子に継承されていること
        assert "singularity" in child.traits
        # stable (D phenotype) ではなく singularity が発現していることを確認
        assert "stable" not in child.traits
