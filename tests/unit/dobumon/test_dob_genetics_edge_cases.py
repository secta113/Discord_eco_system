import pytest

from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.genetics.dob_breeders import StandardBreeder
from logic.dobumon.genetics.dob_mendel import MendelEngine
from logic.dobumon.genetics.traits.registry import TraitRegistry


def test_the_forbidden_sterility_override():
    """背反があっても禁断があれば不妊が維持されることを確認"""
    # 両方の特性を持つ
    traits = ["antinomy", "the_forbidden"]

    # Breeder の内部メソッドを直接検証
    breeder = StandardBreeder()
    _, _, _, is_sterile = breeder._resolve_lifespan_and_illness(
        traits, inbreeding_f=0, is_bara=False, forbidden_depth=1
    )

    # the_forbidden が優先され、不妊（True）であるべき
    assert is_sterile is True


def test_anti_taboo_combat_bonus():
    """対禁忌特性の戦闘ボーナス計算を検証"""
    trait = TraitRegistry.get("anti_taboo")
    me = Dobumon(
        dobumon_id="me",
        owner_id=1,
        name="Hunter",
        gender="M",
        hp=100,
        atk=10,
        defense=10,
        eva=10,
        spd=10,
    )

    # 相手が禁断の場合
    opponent_forbidden = Dobumon(
        dobumon_id="op1",
        owner_id=1,
        name="TheOne",
        gender="M",
        hp=100,
        atk=10,
        defense=10,
        eva=10,
        spd=10,
    )
    opponent_forbidden.traits = ["the_forbidden"]

    mods = trait.on_combat_start(me, opponent_forbidden)
    # 禁断相手には 10倍
    assert mods["atk"] == 10.0
    assert mods["defense"] == 10.0
    assert mods["hp"] == 10.0

    # 相手が禁忌深度を持つ場合
    opponent_depth = Dobumon(
        dobumon_id="op2",
        owner_id=1,
        name="Deep",
        gender="M",
        hp=100,
        atk=10,
        defense=10,
        eva=10,
        spd=10,
    )
    opponent_depth.genetics["forbidden_depth"] = 2

    mods_depth = trait.on_combat_start(me, opponent_depth)
    # 1.0 + (2 * 0.3) = 1.6
    assert mods_depth["atk"] == 1.6
    assert mods_depth["defense"] == 1.6


def test_forbidden_blue_consumption():
    """青の禁忌による寿命消費倍率を検証"""
    dobu = Dobumon(
        dobumon_id="blue",
        owner_id=1,
        name="Blue",
        gender="F",
        hp=100,
        atk=10,
        defense=10,
        eva=10,
        spd=10,
    )
    dobu.traits = ["forbidden_blue"]

    # Dobumon.consumption_mod プロパティを通じて検証 (ベース 1.0 * 青の禁忌 2.0)
    assert dobu.consumption_mod >= 2.0


def test_mendel_resolve_no_confusion():
    """標準的な特性名がアレルに入っていても突然変異と誤認されないことを確認"""
    # potential locus に 'early' (本来は標準特性名) が入っている不正な状態
    genotype = {"potential": ["early", "D"]}
    genetics_meta = {}

    active_traits = MendelEngine.resolve_traits(genotype, genetics_meta)

    # 'early' は突然変異アレルとして抽出されず、Dの表現型（stable）が選ばれるべき
    assert "early" not in active_traits
    assert "stable" in active_traits
