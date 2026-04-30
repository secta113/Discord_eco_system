import pytest

from logic.dobumon.genetics.dob_kinship import KinshipLogic


def test_parse_lineage():
    lineage = ["dobu-1|1|0.0", "dobu-2|2|0.125", "old-id"]
    parsed = KinshipLogic.parse_lineage(lineage)

    assert parsed["dobu-1"] == (1, 0.0)
    assert parsed["dobu-2"] == (2, 0.125)
    assert parsed["old-id"] == (5, 0.0)


def test_calculate_coi_none():
    p1_id = "A"
    p1_parsed = {"S": (1, 0.0)}
    p2_id = "B"
    p2_parsed = {"T": (1, 0.0)}

    coi = KinshipLogic.calculate_coi(p1_id, p1_parsed, p2_id, p2_parsed)
    assert coi == 0.0


def test_calculate_coi_half_sibling():
    # 共通の親 S (F=0) を持つ異母兄弟
    # F = (0.5)^(1+1+1) * (1+0) = 0.5^3 = 0.125
    p1_id = "A"
    p1_parsed = {"S": (1, 0.0)}
    p2_id = "B"
    p2_parsed = {"S": (1, 0.0)}

    coi = KinshipLogic.calculate_coi(p1_id, p1_parsed, p2_id, p2_parsed)
    assert coi == 0.125


def test_calculate_coi_full_sibling():
    # 共通の親 S, T (F=0) を持つ実の兄弟
    # F = (0.5)^3 * (1+0) + (0.5)^3 * (1+0) = 0.125 + 0.125 = 0.25
    p1_id = "A"
    p1_parsed = {"S": (1, 0.0), "T": (1, 0.0)}
    p2_id = "B"
    p2_parsed = {"S": (1, 0.0), "T": (1, 0.0)}

    coi = KinshipLogic.calculate_coi(p1_id, p1_parsed, p2_id, p2_parsed)
    assert coi == 0.25


def test_get_kinship_degree():
    # 親子
    p1_id = "A"
    p1_parsed = {"S": (1, 0.0)}
    p2_id = "S"
    p2_parsed = {"T": (1, 0.0)}

    degree = KinshipLogic.get_kinship_degree(p1_id, p1_parsed, p2_id, p2_parsed)
    assert degree == 1


def test_get_kinship_degree_sibling():
    # 兄弟
    p1_id = "A"
    p1_parsed = {"S": (1, 0.0)}
    p2_id = "B"
    p2_parsed = {"S": (1, 0.0)}

    degree = KinshipLogic.get_kinship_degree(p1_id, p1_parsed, p2_id, p2_parsed)
    assert degree == 2


def test_get_kinship_degree_external():
    # 赤の他人
    p1_id = "A"
    p1_parsed = {"S": (1, 0.0)}
    p2_id = "B"
    p2_parsed = {"T": (1, 0.0)}

    degree = KinshipLogic.get_kinship_degree(p1_id, p1_parsed, p2_id, p2_parsed)
    assert degree is None


def test_calculate_penalties():
    # F=0.25 (実の兄弟)
    penalties = KinshipLogic.calculate_inbreeding_penalties(0.25)
    # lifespan: 1 - 0.5^0.25 = 1 - 0.84 = 16% 減少
    assert penalties["lifespan_penalty_pct"] == 15.9  # 1 - 0.8408... = 0.159...
    # illness: 0.25 * 0.4 = 0.1 = 10% 上昇
    assert penalties["illness_gain_pct"] == 10.0
