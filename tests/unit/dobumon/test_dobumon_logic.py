import pytest

from logic.dobumon.core.dob_models import Dobumon


def test_dobumon_initialization():
    """怒武者の初期化テスト"""
    data = {
        "dobumon_id": "test-uuid-1",
        "owner_id": 123456789,
        "name": "ドブ太郎",
        "gender": "M",
        "hp": 100,
        "atk": 50,
        "defense": 40,
        "eva": 10,
        "spd": 15,
        "iv": {"hp": 1.1, "atk": 1.0, "defense": 0.9, "eva": 1.0, "spd": 1.0},
        "lifespan": 100,
    }
    dobu = Dobumon(**data)
    assert dobu.name == "ドブ太郎"
    assert dobu.gender == "M"
    assert dobu.owner_id == 123456789
    assert dobu.is_alive is True


def test_dobumon_death(monkeypatch):
    """死亡フラグのテスト"""
    # 実際には Dobumon.die() はフラグを見ないが、一貫性のためセット
    monkeypatch.setattr("logic.dobumon.core.dob_manager.DISABLE_DEATH", False)
    dobu = Dobumon(
        dobumon_id="test-uuid-2",
        owner_id=123,
        name="死にかけ",
        gender="F",
        hp=10,
        atk=5,
        defense=5,
        eva=5,
        spd=5,
        iv={},
        lifespan=1,
    )
    assert dobu.is_alive is True
    dobu.die()
    assert dobu.is_alive is False


def test_dobumon_stat_points():
    """ステータス計算の基本テスト（IVの影響など）"""
    dobu_strong = Dobumon(
        dobumon_id="test-uuid-3",
        owner_id=123,
        name="強個体",
        gender="M",
        hp=100,
        atk=50,
        defense=40,
        eva=10,
        spd=15,
        iv={"atk": 1.2},
        lifespan=100,
    )
    assert dobu_strong.iv["atk"] == 1.2


import os

from core.handlers.storage import SQLiteDobumonRepository
from logic.dobumon.core.dob_manager import DobumonManager


def test_manager_creation(tmp_path):
    """マネージャーによる怒武者生成のテスト"""
    db_path = str(tmp_path / "test.db")
    from core.handlers import sql_handler

    sql_handler.init_db(db_path)

    repo = SQLiteDobumonRepository(db_path)
    manager = DobumonManager(repo)
    dobu = manager.create_dobumon(owner_id=123, name="ポチ", source="buyer")

    assert dobu.name == "ポチ"
    assert dobu.owner_id == 123
    assert 90 <= dobu.hp <= 110  # 100 * (0.9 ~ 1.1)


def test_manager_persistence(tmp_path):
    """マネージャーによる永続化のテスト"""
    db_path = str(tmp_path / "test.db")
    from core.handlers import sql_handler

    sql_handler.init_db(db_path)

    repo = SQLiteDobumonRepository(db_path)
    manager = DobumonManager(repo)
    dobu = manager.create_dobumon(owner_id=123, name="タマ")
    manager.save_dobumon(dobu)

    loaded_list = manager.get_user_dobumons(123)
    assert len(loaded_list) == 1
    assert loaded_list[0].name == "タマ"
    assert loaded_list[0].dobumon_id == dobu.dobumon_id
