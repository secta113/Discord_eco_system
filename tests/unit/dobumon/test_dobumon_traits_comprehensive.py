from unittest.mock import MagicMock

import pytest

from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.core.dob_traits import BaseTrait, TraitRegistry
from logic.dobumon.genetics.dob_taboo import TabooLogic
from logic.dobumon.training import TrainingEngine


@pytest.fixture
def sample_dobu():
    return Dobumon(
        dobumon_id="test",
        owner_id="1",
        name="Tester",
        gender="M",
        hp=100.0,
        atk=100.0,
        defense=100.0,
        eva=100.0,
        spd=100.0,
        affection=0,
    )


def test_basic_stat_modifiers(sample_dobu):
    """基本特性のステータス補正が正しく適用されるか検証"""
    # early: hp_mod 1.2, growth_mod 0.8
    early = TraitRegistry.get("early")
    assert early.get_stat_multiplier("hp") == 1.2
    assert early.growth_mod == 0.8

    # late: hp_mod 0.8, growth_mod 1.5
    late = TraitRegistry.get("late")
    assert late.get_stat_multiplier("hp") == 0.8
    assert late.growth_mod == 1.5

    # hardy: illness_mod 0.5, lifespan_mod 1.2
    hardy = TraitRegistry.get("hardy")
    assert hardy.illness_mod == 0.5
    assert hardy.lifespan_mod == 1.2

    # frail: illness_mod 2.0, eva_mod 1.2
    frail = TraitRegistry.get("frail")
    assert frail.illness_mod == 2.0
    assert frail.get_stat_multiplier("eva") == 1.2


def test_stable_and_burst(sample_dobu):
    """安定（stable）と爆発（burst）の固有挙動を検証"""
    # stable: variation_range (0.95, 1.05)
    stable = TraitRegistry.get("stable")
    assert stable.variation_range == (0.95, 1.05)

    # burst: great_success_mod 2.0
    burst = TraitRegistry.get("burst")
    assert burst.great_success_mod == 2.0
    assert burst.mutation_mod == 2.0


def test_rare_mutations():
    """希少突然変異の報酬・ステータス補正を検証"""
    # gold_horn: reward_mod 1.1, def_mod 1.2
    gh = TraitRegistry.get("gold_horn")
    assert gh.reward_mod == 1.1
    assert gh.get_stat_multiplier("def") == 1.2

    # red_back: atk_mod 1.3
    assert TraitRegistry.get("red_back").get_stat_multiplier("atk") == 1.3

    # odd_eye: eva_mod 1.3
    assert TraitRegistry.get("odd_eye").get_stat_multiplier("eva") == 1.3

    # blue_blood: hp_mod 1.3, illness_mod 0.5
    bb = TraitRegistry.get("blue_blood")
    assert bb.get_stat_multiplier("hp") == 1.3
    assert bb.illness_mod == 0.5


def test_conceptual_mutations_complex(sample_dobu):
    """概念的突然変異の複雑な挙動（Unlimited, Undead等）を検証"""
    # Unlimited: ignores decay
    unlimited = TraitRegistry.get("unlimited")
    decayed_val = 0.2  # 1000ステータス時の減衰
    assert unlimited.on_growth_multiplier(sample_dobu, decayed_val) == 1.0

    # Undead: prevents death
    undead = TraitRegistry.get("undead")
    assert undead.modifies_battle_death() is True
    assert undead.lifespan_mod == 5.0

    # Parasitic: 0.1x training, 3x reward
    parasitic = TraitRegistry.get("parasitic")
    assert parasitic.on_growth_multiplier(sample_dobu, 1.0) == 0.1
    exp, pts = parasitic.on_combat_reward(100, 1000)
    assert exp == 300
    assert pts == 3000


def test_glass_blade_extreme_stats():
    """硝子の刃（glass_blade）の極端なステータス補正を検証"""
    gb = TraitRegistry.get("glass_blade")
    assert gb.get_stat_multiplier("atk") == 2.5
    assert gb.get_stat_multiplier("spd") == 2.5
    assert gb.get_stat_multiplier("hp") == 0.5
    assert gb.get_stat_multiplier("def") == 0.5


def test_taboo_combat_anti_taboo(sample_dobu):
    """対禁忌（anti_taboo）の戦闘補正を検証"""
    sample_dobu.traits = ["anti_taboo"]

    # 相手が禁断（the_forbidden）の場合、全ステータス10倍
    opponent = Dobumon("opp", "2", "ForbiddenOne", "M", 100, 100, 100, 100, 100)
    opponent.traits = ["the_forbidden"]

    mods = TabooLogic.get_combat_modifiers(sample_dobu, opponent)
    for stat in ["atk", "defense", "hp", "eva", "spd"]:
        assert mods[stat] == 10.0

    # 相手が禁忌深度 2 の場合、ATK/DEF +60% (30% * 2)
    opponent.traits = []
    opponent.genetics["forbidden_depth"] = 2
    mods_depth = TabooLogic.get_combat_modifiers(sample_dobu, opponent)
    assert mods_depth["atk"] == pytest.approx(1.6)
    assert mods_depth["defense"] == pytest.approx(1.6)
    assert mods_depth["hp"] == 1.0  # 変化なし


def test_taboo_lifespan_negation(sample_dobu):
    """背反（antinomy）と禁断（the_forbidden）による寿命加速の無効化を検証"""
    sample_dobu.genetics["forbidden_depth"] = 3
    base_consumption = 1.0

    # 補正なしの場合、1.2^3 = 1.728 倍の加速
    accelerated = TabooLogic.apply_status_modifiers(sample_dobu, base_consumption)
    assert accelerated == pytest.approx(1.728)

    # 背反を持っている場合、加速が無効化される (1.0倍)
    sample_dobu.traits = ["antinomy"]
    negated = TabooLogic.apply_status_modifiers(sample_dobu, base_consumption)
    assert negated == 1.0

    # 禁断を持っている場合も同様
    sample_dobu.traits = ["the_forbidden"]
    negated_forbidden = TabooLogic.apply_status_modifiers(sample_dobu, base_consumption)
    assert negated_forbidden == 1.0


def test_forbidden_growth_boost(sample_dobu):
    """禁断（the_forbidden）による成長倍率補正を検証"""
    sample_dobu.traits = ["the_forbidden"]
    sample_dobu.genetics["forbidden_depth"] = 5

    base_growth = 1.0
    boosted = TabooLogic.get_growth_multiplier(sample_dobu, base_growth)
    # depth=5 / 0.7 ≒ 7.1428
    assert boosted == pytest.approx(5.0 / 0.7)

    # 深度0でも最低1/0.7倍
    sample_dobu.genetics["forbidden_depth"] = 0
    boosted_zero = TabooLogic.get_growth_multiplier(sample_dobu, base_growth)
    assert boosted_zero == pytest.approx(1.0 / 0.7)


def test_aesthetic_trait_stat_modifier(sample_dobu):
    """美形（aesthetic）特性のステータス補正を検証"""
    aesthetic = TraitRegistry.get("aesthetic")
    # 美形特性は回避性能を 1.05倍 にする
    assert aesthetic.get_stat_multiplier("eva") == 1.05
    assert aesthetic.get_stat_multiplier("hp") == 1.0
    assert aesthetic.get_stat_multiplier("atk") == 1.0


def test_normal_trait_stat_modifier(sample_dobu):
    """通常（normal）特性が一切の補正を行わないことを検証"""
    # normal は実装上クラスが存在せず、デフォルト処理される
    normal = TraitRegistry.get("normal")
    assert type(normal).__name__ == "BaseMutationTrait"  # registry には存在しない

    # ベースの特性適用ロジックでも、TraitNotFound ではなく None 扱い
    # Dobumon クラスの get_total_stat_multiplier などで例外が出ないか模擬検証
    # sample_dobu に normal 特性を設定
    sample_dobu.traits = ["normal"]

    # 全ステータス倍率が 1.0 であることを確認
    for stat in ["hp", "atk", "defense", "eva", "spd", "illness", "lifespan", "growth"]:
        multiplier = 1.0
        for trait_key in sample_dobu.traits:
            trait = TraitRegistry.get(trait_key)
            if trait:
                if stat == "illness":
                    multiplier *= trait.illness_mod
                elif stat == "lifespan":
                    multiplier *= trait.lifespan_mod
                elif stat == "growth":
                    multiplier *= trait.growth_mod
                else:
                    multiplier *= trait.get_stat_multiplier(stat)
        assert multiplier == 1.0
