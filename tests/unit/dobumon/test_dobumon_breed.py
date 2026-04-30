import os

import pytest

from core.handlers import sql_handler
from core.handlers.storage import SQLiteDobumonRepository
from logic.dobumon.core.dob_exceptions import DobumonError
from logic.dobumon.core.dob_manager import DobumonManager


def test_dobumon_breeding_standard(tmp_path):
    """標準的な交配（M×F）のテスト"""
    db_path = str(tmp_path / "test_breed.db")
    sql_handler.init_db(db_path)
    repo = SQLiteDobumonRepository(db_path)
    manager = DobumonManager(repo)

    # 親1: オス
    p1 = manager.create_dobumon(owner_id=123, name="父ドブ")
    p1.gender = "M"
    p1.hp = 100
    p1.atk = 50
    p1.lifespan = 80.0

    p1.max_lifespan = 100.0
    manager.save_dobumon(p1)

    # 親2: メス
    p2 = manager.create_dobumon(owner_id=123, name="母ドブ")
    p2.gender = "F"
    p2.hp = 100
    p2.atk = 50
    p2.lifespan = 80.0

    p2.max_lifespan = 100.0
    manager.save_dobumon(p2)

    # 交配実行
    result = manager.breed_dobumon(p1.dobumon_id, p2.dobumon_id, "子ドブ")

    assert result["success"] is True
    child = result["child"]
    assert child.name == "子ドブ"
    assert child.generation == 2

    # 親の寿命が減っているか確認 (20減少)
    p1_after = manager.get_dobumon(p1.dobumon_id)
    p2_after = manager.get_dobumon(p2.dobumon_id)
    assert p1_after.lifespan == 60.0
    assert p2_after.lifespan == 60.0


def test_yuri_breeding(tmp_path):
    """百合交配（F×F）のテスト：特性の継承と短命化"""
    db_path = str(tmp_path / "test_yuri.db")
    sql_handler.init_db(db_path)
    repo = SQLiteDobumonRepository(db_path)
    manager = DobumonManager(repo)

    p1 = manager.create_dobumon(owner_id=123, name="メス1")
    p1.gender = "F"
    p1.lifespan = 80.0

    p1.max_lifespan = 100.0
    manager.save_dobumon(p1)

    p2 = manager.create_dobumon(owner_id=123, name="メス2")
    p2.gender = "F"
    p2.lifespan = 80.0

    p2.max_lifespan = 100.0
    manager.save_dobumon(p2)

    result = manager.breed_dobumon(p1.dobumon_id, p2.dobumon_id, "百合の結晶")
    assert result["success"] is True
    child = result["child"]

    # 「百合」の特性（青の禁忌）
    assert "forbidden_blue" in child.traits
    assert child.can_extend_lifespan is False
    # 寿命が通常（~120）の60%程度 (72前後)。特性により延びることもあるため90以下を許容
    assert 30 <= child.lifespan <= 90


def test_bara_breeding(tmp_path):
    """薔薇交配（M×M）のテスト：戦闘特化と生殖不能"""
    db_path = str(tmp_path / "test_bara.db")
    sql_handler.init_db(db_path)
    repo = SQLiteDobumonRepository(db_path)
    manager = DobumonManager(repo)

    p1 = manager.create_dobumon(owner_id=123, name="オス1")
    p1.gender = "M"
    p1.lifespan = 80.0

    p1.max_lifespan = 100.0
    manager.save_dobumon(p1)

    p2 = manager.create_dobumon(owner_id=123, name="オス2")
    p2.gender = "M"
    p2.lifespan = 80.0

    p2.max_lifespan = 100.0
    manager.save_dobumon(p2)

    result = manager.breed_dobumon(p1.dobumon_id, p2.dobumon_id, "薔薇の騎士")
    assert result["success"] is True
    child = result["child"]

    # 「薔薇」の特性（赤の禁忌）
    assert "forbidden_red" in child.traits
    assert child.is_sterile is True
    # ステータス補正 (atk が他の平均より高くなりやすい)
    # IV または 実数値が親と同等以上（補正1.3倍があるため）
    assert child.atk >= 30


def test_breeding_failures(tmp_path):
    """交配失敗ケースの検証"""
    db_path = str(tmp_path / "test_fail.db")
    sql_handler.init_db(db_path)
    repo = SQLiteDobumonRepository(db_path)
    manager = DobumonManager(repo)

    # 1. 自己交配の禁止
    p1 = manager.create_dobumon(owner_id=123, name="孤独なドブ")
    p1.lifespan = 80.0

    p1.max_lifespan = 100.0
    manager.save_dobumon(p1)
    with pytest.raises(DobumonError) as excinfo:
        manager.breed_dobumon(p1.dobumon_id, p1.dobumon_id, "クローン")
    assert "同一の個体同士" in str(excinfo.value)

    # 2. 生殖不能個体（薔薇）の交配禁止
    p2 = manager.create_dobumon(owner_id=123, name="オスA")
    p2.gender = "M"
    p2.lifespan = 80.0
    p2.max_lifespan = 100.0
    manager.save_dobumon(p2)
    p3 = manager.create_dobumon(owner_id=123, name="オスB")
    p3.gender = "M"
    p3.lifespan = 80.0
    p3.max_lifespan = 100.0
    manager.save_dobumon(p3)
    res_bara = manager.breed_dobumon(p2.dobumon_id, p3.dobumon_id, "薔薇の子")
    bara_child = res_bara["child"]
    bara_child.lifespan = 80.0
    bara_child.max_lifespan = 100.0
    manager.save_dobumon(bara_child)
    assert bara_child.is_sterile is True

    p4 = manager.create_dobumon(owner_id=123, name="普通のメス")
    p4.gender = "F"
    p4.lifespan = 80.0
    p4.max_lifespan = 100.0
    manager.save_dobumon(p4)
    with pytest.raises(DobumonError) as excinfo:
        manager.breed_dobumon(bara_child.dobumon_id, p4.dobumon_id, "生まれない子")
    assert "生殖能力のない" in str(excinfo.value)


def test_young_breeding_allowed(tmp_path):
    """幼年期（寿命85%以上）の個体が交配できることを検証"""
    db_path = str(tmp_path / "test_young.db")
    sql_handler.init_db(db_path)
    repo = SQLiteDobumonRepository(db_path)
    manager = DobumonManager(repo)

    p1 = manager.create_dobumon(owner_id=1, name="若き父")
    p1.lifespan = 95.0  # 幼年期
    p1.max_lifespan = 100.0  # 95/100 = 0.95 > 0.8 → young
    manager.save_dobumon(p1)

    p2 = manager.create_dobumon(owner_id=1, name="若き母")
    p2.lifespan = 95.0  # 幼年期
    p2.max_lifespan = 100.0
    p2.gender = "F"
    manager.save_dobumon(p2)

    # 交配が成功するはず
    result = manager.breed_dobumon(p1.dobumon_id, p2.dobumon_id, "早すぎた子")
    assert result["success"] is True
    assert result["child"].name == "早すぎた子"
    assert result["child"].generation == 2


def test_inheritance_decay_senior(tmp_path):
    """熟練期・晩年期の親からの遺伝減衰を検証"""
    db_path = str(tmp_path / "test_decay.db")
    sql_handler.init_db(db_path)
    repo = SQLiteDobumonRepository(db_path)
    manager = DobumonManager(repo)

    # 全盛期のペア (遺伝補正 1.0)
    p1 = manager.create_dobumon(owner_id=1, name="全盛父")
    p1.lifespan = 50.0  # 全盛期
    p1.max_lifespan = 100.0  # 50/100 = 0.5 → prime
    p1.iv = {"hp": 1.0, "atk": 1.0, "defense": 1.0, "eva": 1.0, "spd": 1.0}
    manager.save_dobumon(p1)

    p2 = manager.create_dobumon(owner_id=1, name="全盛母")
    p2.lifespan = 50.0  # 全盛期
    p2.max_lifespan = 100.0
    p2.gender = "F"
    p2.iv = {"hp": 1.0, "atk": 1.0, "defense": 1.0, "eva": 1.0, "spd": 1.0}
    manager.save_dobumon(p2)

    res_prime = manager.breed_dobumon(p1.dobumon_id, p2.dobumon_id, "全盛の子")
    iv_prime = res_prime["child"].iv["atk"]

    # 晩年期のペア (遺伝補正 0.5)
    p3 = manager.create_dobumon(owner_id=1, name="晩年父")
    p3.lifespan = 5.0  # 晩年期
    p3.max_lifespan = 100.0  # 5/100 = 0.05 → twilight
    p3.iv = {"hp": 1.0, "atk": 1.0, "defense": 1.0, "eva": 1.0, "spd": 1.0}
    manager.save_dobumon(p3)

    p4 = manager.create_dobumon(owner_id=1, name="晩年母")
    p4.lifespan = 5.0  # 晩年期
    p4.max_lifespan = 100.0
    p4.gender = "F"
    p4.iv = {"hp": 1.0, "atk": 1.0, "defense": 1.0, "eva": 1.0, "spd": 1.0}
    manager.save_dobumon(p4)

    res_twilight = manager.breed_dobumon(p3.dobumon_id, p4.dobumon_id, "晩年の子")
    iv_twilight = res_twilight["child"].iv["atk"]

    # 晩年の子のIVは、全盛の子の半分（付近）になっているはず
    # (誤差があるため、明らかに低いことを確認)
    assert iv_twilight < iv_prime * 0.7


def test_yuri_chain_and_inheritance(tmp_path):
    """F×F（百合）交配の連鎖と、負の遺伝の継承（延命不可）を検証"""
    db_path = str(tmp_path / "test_yuri_chain.db")
    sql_handler.init_db(db_path)
    repo = SQLiteDobumonRepository(db_path)
    manager = DobumonManager(repo)

    # 第1世代 (F×F)
    p1 = manager.create_dobumon(owner_id=123, name="母A")
    p1.gender = "F"
    p1.lifespan = 80.0
    p1.max_lifespan = 100.0
    p2 = manager.create_dobumon(owner_id=123, name="母B")
    p2.gender = "F"
    p2.lifespan = 80.0
    p2.max_lifespan = 100.0
    manager.save_dobumon(p1)
    manager.save_dobumon(p2)

    res1 = manager.breed_dobumon(p1.dobumon_id, p2.dobumon_id, "百合の子1")
    child1 = res1["child"]
    assert "forbidden_blue" in child1.traits
    # 「背反 (antinomy)」が発現（突然変異）していない限り、延命は不可
    if "antinomy" in child1.traits:
        assert child1.can_extend_lifespan is True
    else:
        assert child1.can_extend_lifespan is False

    # 第2世代 (通常の交配 M×F でも「禁忌の血」が継承されるか)
    child1.gender = "F"
    child1.lifespan = 80.0
    child1.max_lifespan = 100.0
    manager.save_dobumon(child1)
    p_male = manager.create_dobumon(owner_id=123, name="普通のオス")
    p_male.gender = "M"
    p_male.lifespan = 80.0
    p_male.max_lifespan = 100.0
    manager.save_dobumon(p_male)

    res2 = manager.breed_dobumon(child1.dobumon_id, p_male.dobumon_id, "継承の子")
    child2 = res2["child"]
    # 血統が混ざっているので禁忌因子が継承される
    assert "forbidden_blue" in child2.traits
    # 「背反 (antinomy)」が同時に発現（突然変異）していない限り、延命は不可
    if "antinomy" in child2.traits:
        assert child2.can_extend_lifespan is True
    else:
        assert child2.can_extend_lifespan is False
