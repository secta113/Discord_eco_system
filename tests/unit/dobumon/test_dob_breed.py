from unittest.mock import patch

import pytest

from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.genetics.dob_breeders import BreedingFactory


@patch("random.random", return_value=0.5)
def test_standard_breeding(mock_random):
    """標準的な交配（M×F）のテスト"""
    p1 = Dobumon(
        dobumon_id="M1",
        owner_id=1,
        name="父",
        gender="M",
        hp=100,
        atk=100,
        defense=100,
        eva=10,
        spd=10,
        attribute="fire",
        lifespan=100,
    )
    p2 = Dobumon(
        dobumon_id="F1",
        owner_id=1,
        name="母",
        gender="F",
        hp=100,
        atk=100,
        defense=100,
        eva=10,
        spd=10,
        attribute="water",
        lifespan=100,
    )

    breeder = BreedingFactory.get_breeder(p1, p2)
    child = breeder.breed(p1, p2, "標準丸")

    assert child.name == "標準丸"
    assert child.generation == 2
    assert child.is_sterile is False
    assert child.can_extend_lifespan is True
    # ステータスが親の平均付近（揺らぎ±10%以内 or 突然変異 or 特性補正）
    # 劣性遺伝でステータスマイナスの特性（晩成、病弱など）を複数引いた場合、HPは理論上下限72付近まで低下するため70とする。最大値は突然変異(1.4) + 特性(early=1.2)で 180 を超える可能性があるため 200 に緩和
    assert 70 <= child.hp <= 200


def test_yuri_breeding_risks():
    """百合交配（F×F）のリスクと特性のテスト（強力な継承）"""
    p1 = Dobumon(
        dobumon_id="F1",
        owner_id=1,
        name="母1",
        gender="F",
        hp=100,
        atk=10,
        defense=10,
        eva=10,
        spd=10,
        lifespan=100,
        iv={"hp": 1.0, "atk": 1.0, "defense": 1.0, "eva": 1.0, "spd": 1.0},
    )
    p2 = Dobumon(
        dobumon_id="F2",
        owner_id=1,
        name="母2",
        gender="F",
        hp=100,
        atk=10,
        defense=10,
        eva=10,
        spd=10,
        lifespan=100,
        iv={"hp": 1.0, "atk": 1.0, "defense": 1.0, "eva": 1.0, "spd": 1.0},
    )

    breeder = BreedingFactory.get_breeder(p1, p2)
    child = breeder.breed(p1, p2, "百合子")

    # 青の禁忌は短命化する。特性により補正されることもあるため90以下かを検証
    assert child.lifespan <= 90
    assert "forbidden_blue" in child.traits
    assert child.genetics["has_forbidden_blue"] is True
    assert child.can_extend_lifespan is False

    # 強力な継承 (IVが1.15倍程度にブーストされる)
    # 理論上の最大値: (1.4 + 0.3) * 1.15 = 1.955 -> 1.96
    assert 1.0 <= child.iv["hp"] <= 1.96


def test_bara_breeding_traits():
    """薔薇交配（M×M）の特性と制限のテスト（成長最大化・高初期値・極端病弱）"""
    p1 = Dobumon(
        dobumon_id="M1",
        owner_id=1,
        name="父1",
        gender="M",
        hp=100,
        atk=100,
        defense=10,
        eva=10,
        spd=100,
        iv={"hp": 1.0, "atk": 1.0, "defense": 1.0, "eva": 1.0, "spd": 1.0},
    )
    p2 = Dobumon(
        dobumon_id="M2",
        owner_id=1,
        name="父2",
        gender="M",
        hp=100,
        atk=100,
        defense=10,
        eva=10,
        spd=100,
        iv={"hp": 1.0, "atk": 1.0, "defense": 1.0, "eva": 1.0, "spd": 1.0},
    )

    breeder = BreedingFactory.get_breeder(p1, p2)
    child = breeder.breed(p1, p2, "薔薇男")

    assert "forbidden_red" in child.traits
    assert child.genetics["has_forbidden_red"] is True
    assert child.is_sterile is True
    assert child.can_extend_lifespan is False

    # 極端な病弱 (+0.15)。特性によりベース値が0になることもあるため 0.15以上かを検証
    assert child.illness_rate >= 0.15

    # 成長の最大化 (IV 1.2倍) & 初期値の底上げ (1.2倍)
    # 親Atk 100, 親IV 1.0 -> 子IV ~1.2
    # Base 50 * 1.2 (iv) + 15 (inherit) = 75
    # 75 * 1.2 (bara_stat_boost) = 90
    # 90 * 1.5 (forbidden_red_atk_mod) = 135
    assert child.atk >= 120


@patch("logic.dobumon.genetics.dob_breeders.random.random")
def test_aesthetic_inheritance(mock_random):
    """美形（aesthetic）の継承テスト (劣性ホモ)"""
    mock_random.return_value = 1.0  # 突発的な突然変異を防ぐ
    p1 = Dobumon(
        dobumon_id="M1",
        owner_id=1,
        name="P1",
        gender="M",
        hp=100,
        atk=10,
        defense=10,
        eva=10,
        spd=10,
        genetics={"genotype": {"body": ["r", "r"]}},
    )
    p2 = Dobumon(
        dobumon_id="F1",
        owner_id=1,
        name="P2",
        gender="F",
        hp=100,
        atk=10,
        defense=10,
        eva=10,
        spd=10,
        genetics={"genotype": {"body": ["r", "r"]}},
    )

    child = BreedingFactory.get_breeder(p1, p2).breed(p1, p2, "美形児")
    assert "aesthetic" in child.traits
    assert child.genetics["genotype"]["body"] == ["r", "r"]


@patch("random.random", return_value=0.5)
def test_forbidden_blood_inheritance(mock_random):
    """禁忌の血統が交配後も引き継がれるかのテスト"""
    # 1. 青の禁忌個体を作成
    p1 = Dobumon(
        dobumon_id="F1",
        owner_id=1,
        name="F1",
        gender="F",
        hp=100,
        atk=10,
        defense=10,
        eva=10,
        spd=10,
    )
    p2 = Dobumon(
        dobumon_id="F2",
        owner_id=1,
        name="F2",
        gender="F",
        hp=100,
        atk=10,
        defense=10,
        eva=10,
        spd=10,
    )
    yuri_child = BreedingFactory.get_breeder(p1, p2).breed(p1, p2, "禁忌の娘")

    assert yuri_child.genetics["has_forbidden_blue"] is True

    # 2. 禁忌の娘(F)と、普通のオス(M)を交配
    normal_male = Dobumon(
        dobumon_id="M1",
        owner_id=1,
        name="M1",
        gender="M",
        hp=100,
        atk=10,
        defense=10,
        eva=10,
        spd=10,
    )

    # 普通の配合だが、血統を引き継ぐ
    grand_child = BreedingFactory.get_breeder(yuri_child, normal_male).breed(
        yuri_child, normal_male, "孫"
    )

    assert grand_child.genetics["has_forbidden_blue"] is True
    assert "forbidden_blue" in grand_child.traits
    assert grand_child.can_extend_lifespan is False
