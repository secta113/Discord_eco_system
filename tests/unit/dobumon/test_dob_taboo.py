import pytest

from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.dob_battle.dob_calculator import BattleCalculator
from logic.dobumon.genetics.dob_breeders import StandardBreeder
from logic.dobumon.genetics.dob_taboo import TabooLogic


def test_anti_taboo_transformation():
    # 禁忌因子（赤または青）を持つ個体に対禁忌が発現した場合、背反に変化する
    traits = ["anti_taboo", "early"]
    genetics_meta = {"has_forbidden_red": True}

    new_traits, is_forbidden, new_meta = TabooLogic.resolve_taboo_transformation(
        traits, genetics_meta, "M"
    )

    assert "antinomy" in new_traits
    assert "anti_taboo" not in new_traits
    assert "early" in new_traits
    assert is_forbidden is False

    # 因子がない場合は変化しない
    traits_2 = ["anti_taboo"]
    genetics_meta_2 = {}
    new_traits_2, _, _ = TabooLogic.resolve_taboo_transformation(traits_2, genetics_meta_2, "M")
    assert "anti_taboo" in new_traits_2
    assert "antinomy" not in new_traits_2


def test_forbidden_trigger():
    # 背反 + 赤の禁忌因子 + 青の禁忌因子 -> 禁断
    traits = ["antinomy"]
    genetics_meta = {"has_forbidden_red": True, "has_forbidden_blue": True}

    new_traits, is_forbidden, new_meta = TabooLogic.resolve_taboo_transformation(
        traits, genetics_meta, "M"
    )

    assert "the_forbidden" in new_traits
    assert "antinomy" not in new_traits
    assert is_forbidden is True


def test_depth_inheritance_bypass():
    # 通常時: max(p1, p2) + bonus
    d1 = TabooLogic.calculate_child_forbidden_depth(
        2, 5, is_taboo_breeding=True, is_forbidden_trigger=False
    )
    assert d1 == 6  # max(2, 5) + 1

    # 禁断発現時: sum(p1, p2) + bonus + 2
    d2 = TabooLogic.calculate_child_forbidden_depth(
        2, 5, is_taboo_breeding=True, is_forbidden_trigger=True
    )
    assert d2 == 10  # 2 + 5 + 1 + 2


def test_combat_multipliers():
    # Mock Dobumons
    attacker = Dobumon(
        dobumon_id="a",
        owner_id=1,
        name="Attacker",
        gender="M",
        hp=100,
        atk=10,
        defense=10,
        eva=10,
        spd=10,
    )
    defender = Dobumon(
        dobumon_id="d",
        owner_id=1,
        name="Defender",
        gender="F",
        hp=100,
        atk=10,
        defense=10,
        eva=10,
        spd=10,
    )

    # 1. 対禁忌 vs 深度3 (攻撃側バフ)
    attacker.traits = ["anti_taboo"]
    defender.genetics = {"forbidden_depth": 3}
    a_mods = TabooLogic.get_combat_modifiers(attacker, defender)
    assert a_mods["atk"] == 1.9  # 1.0 + 3 * 0.3
    assert a_mods["defense"] == 1.9

    # 2. vs 禁断 (対禁忌あり/アタッカー)
    defender.traits = ["the_forbidden"]
    a_mods = TabooLogic.get_combat_modifiers(attacker, defender)
    assert a_mods["atk"] == 10.0
    assert a_mods["hp"] == 10.0

    # 3. vs 禁断 (対禁忌なし/アタッカー)
    attacker.traits = []
    a_mods = TabooLogic.get_combat_modifiers(attacker, defender)
    assert a_mods["atk"] == 1.0
    assert a_mods["hp"] == 1.0

    # 4. 対禁忌側が防御に回った場合 (対禁忌 vs 禁断)
    # アタッカー: 禁断
    # ディフェンダー: 対禁忌
    attacker = Dobumon(
        dobumon_id="f",
        owner_id=1,
        name="Forbidden",
        gender="M",
        hp=100,
        atk=10,
        defense=10,
        eva=10,
        spd=10,
    )
    attacker.traits = ["the_forbidden"]
    defender = Dobumon(
        dobumon_id="at",
        owner_id=1,
        name="AntiTaboo",
        gender="F",
        hp=100,
        atk=10,
        defense=10,
        eva=10,
        spd=10,
    )
    defender.traits = ["anti_taboo"]

    # ディフェンダー(対禁忌者)の補正を取得
    d_mods = TabooLogic.get_combat_modifiers(defender, attacker)
    assert d_mods["defense"] == 10.0  # 防御側でも10倍バフが乗るはず
    assert d_mods["eva"] == 10.0


def test_antinomy_sterility_override():
    # 背反は不妊を無効化する
    breeder = StandardBreeder()
    # 内部の _resolve_lifespan_and_illness をテスト
    traits = ["forbidden_red", "antinomy"]
    lifespan, illness, can_extend, is_sterile = breeder._resolve_lifespan_and_illness(
        traits, 0, False, 5
    )

    assert is_sterile is False
    assert can_extend is True


def test_forbidden_restrictions():
    # 禁断は不妊かつ延命不可
    breeder = StandardBreeder()
    traits = ["the_forbidden"]
    lifespan, illness, can_extend, is_sterile = breeder._resolve_lifespan_and_illness(
        traits, 0, False, 10
    )

    assert is_sterile is True
    assert can_extend is False


def test_first_generation_taboo_transformation():
    # オス同士(Bara)の第一世代で、対禁忌アレルを持つ子が誕生した際、即座に背反になるか
    from logic.dobumon.core.dob_models import Dobumon
    from logic.dobumon.genetics.dob_mendel import MendelEngine

    p1 = Dobumon(
        dobumon_id="p1",
        owner_id=1,
        name="P1",
        gender="M",
        hp=100,
        atk=10,
        defense=10,
        eva=10,
        spd=10,
    )
    p2 = Dobumon(
        dobumon_id="p2",
        owner_id=1,
        name="P2",
        gender="M",
        hp=100,
        atk=10,
        defense=10,
        eva=10,
        spd=10,
    )
    # 両親は禁忌因子なし
    p1.genetics = {"genotype": MendelEngine.get_initial_genotype(), "forbidden_depth": 0}
    p2.genetics = {"genotype": MendelEngine.get_initial_genotype(), "forbidden_depth": 0}

    # 子が anti_taboo を継承するように設定
    import random

    random.seed(42)

    child_geno = MendelEngine.get_initial_genotype()
    child_geno["potential"] = ["anti_taboo", "stable"]

    # 修正されたロジックフロー
    # 1. genetics_meta 構築
    genetics_meta = {}
    is_bara = p1.gender == "M" and p2.gender == "M"
    if is_bara:
        genetics_meta["has_forbidden_red"] = True

    # 2. traits 解決
    gender = "M"
    traits = MendelEngine.resolve_traits(child_geno, genetics_meta, gender=gender)
    traits, _, _ = TabooLogic.resolve_taboo_transformation(traits, genetics_meta, gender=gender)

    # 第一世代で背反になっているはず
    assert "antinomy" in traits
    assert "anti_taboo" not in traits


def test_taboo_gender_locking():
    # 通常個体（背反・禁断でない）の場合、性別に合わない因子と特性が除去される

    # 1. オスで青因子保持 -> 青因子除去、青特性除去
    traits = ["forbidden_blue", "early"]
    meta = {"has_forbidden_blue": True}
    new_traits, _, new_meta = TabooLogic.resolve_taboo_transformation(traits, meta, "M")

    assert "forbidden_blue" not in new_traits
    assert "has_forbidden_blue" not in new_meta
    assert "early" in new_traits

    # 2. 背反個体なら性別不一致でも維持される (昇華)
    traits_a = ["antinomy", "forbidden_blue"]
    meta_a = {"has_forbidden_blue": True}
    new_traits_a, _, new_meta_a = TabooLogic.resolve_taboo_transformation(traits_a, meta_a, "M")

    assert "forbidden_blue" in new_traits_a
    assert "has_forbidden_blue" in new_meta_a
    assert "antinomy" in new_traits_a
