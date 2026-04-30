import pytest

from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.genetics.dob_breeders import StandardBreeder


@pytest.fixture
def breeder():
    return StandardBreeder()


def create_mock_dobu(name, lineage=None, inbreeding_f=0.0):
    if lineage is None:
        lineage = []
    # genetics に inbreeding_debt として F値 を格納
    return Dobumon(
        dobumon_id=name,
        owner_id=1,
        name=name,
        gender="M",
        hp=100.0,
        atk=10.0,
        defense=10.0,
        eva=10.0,
        spd=10.0,
        lifespan=100.0,
        max_lifespan=100.0,
        lineage=lineage,
        genetics={"inbreeding_debt": inbreeding_f},
    )


def test_coi_none(breeder):
    """全く血縁のない個体同士の交配 (F=0.0)"""
    p1 = create_mock_dobu("FATHER")
    p2 = create_mock_dobu("MOTHER")
    child = breeder.breed(p1, p2, "CHILD")
    assert child.genetics["inbreeding_debt"] == 0.0
    # 特性(late, early, frail等)による補正を考慮して範囲を広げる
    assert child.lifespan >= 40.0


def test_coi_sibling(breeder):
    """初回の兄弟交配 (F=0.25)"""
    p1 = create_mock_dobu("FATHER")
    p2 = create_mock_dobu("MOTHER")
    # 兄弟を作成
    c1 = breeder.breed(p1, p2, "SON")
    c2 = breeder.breed(p1, p2, "DAUGHTER")

    # 兄妹交配
    grandchild = breeder.breed(c1, c2, "GRANDCHILD")
    assert grandchild.genetics["inbreeding_debt"] == 0.25
    # 寿命ペナルティ: 100 * (0.5^0.25) ≒ 84
    # 初期寿命 80-120 の範囲なので、概ね 67-100 程度になる
    assert grandchild.lifespan < 110


def test_coi_continuous_inbreeding(breeder):
    """累代兄弟交配 (Fの上昇)"""
    p1 = create_mock_dobu("F1")
    p2 = create_mock_dobu("M1")

    # Gen 2: F=0.25
    c1 = breeder.breed(p1, p2, "C1")
    c2 = breeder.breed(p1, p2, "C2")

    # Gen 3: F=0.3125
    gc1 = breeder.breed(c1, c2, "GC1")
    gc2 = breeder.breed(c1, c2, "GC2")
    assert gc1.genetics["inbreeding_debt"] == 0.25

    # Gen 4: F = 0.125(1 + 0.25) + 0.125(1 + 0.25) = 0.3125
    ggc = breeder.breed(gc1, gc2, "GGC")
    assert ggc.genetics["inbreeding_debt"] == 0.3125


def test_coi_parent_child(breeder):
    """親子交配 (F=0.25)"""
    father = create_mock_dobu("FATHER")
    mother = create_mock_dobu("MOTHER")
    daughter = breeder.breed(father, mother, "DAUGHTER")

    # 父 x 娘
    inbred_child = breeder.breed(father, daughter, "INBRED")
    assert inbred_child.genetics["inbreeding_debt"] == 0.25


def test_coi_compatibility_old_format(breeder):
    """旧形式 (IDのみのリスト) との互換性"""
    # 共通先祖 "ROOT" を持つが、形式が古い
    # 旧形式は depth 5 と見なされるため、子は depth 6 になり、デフォルト設定(max_depth=5)ではリストから消える。
    # ここでは計算自体が行われることを確認する。
    p1 = create_mock_dobu("P1", lineage=["ROOT"])
    p2 = create_mock_dobu("P2", lineage=["ROOT"])

    child = breeder.breed(p1, p2, "CHILD")
    # 6親等（はとこ）以上の関係となるため、新仕様では COI = 0.0 となる
    assert child.genetics["inbreeding_debt"] == 0.0
    # 5代前(depth 5)だった ROOT は子は6代前になるため、リストからは除外されるのが正しい挙動
    assert "ROOT" not in [entry.split("|")[0] for entry in child.lineage]
