import datetime

import pytest

from core.handlers import sql_handler
from core.handlers.storage import SQLiteDobumonRepository
from logic.dobumon.core.dob_manager import DobumonManager
from logic.dobumon.core.dob_models import Dobumon


def test_daily_reset_logic(tmp_path):
    """日付変更時のカウントリセット検証"""
    db_path = str(tmp_path / "test_reset.db")
    sql_handler.init_db(db_path)
    repo = SQLiteDobumonRepository(db_path)
    manager = DobumonManager(repo)

    dobu = manager.create_dobumon(owner_id=123, name="リセットドブ")
    dobu.today_train_count = 5
    dobu.today_wild_battle_count = 3
    dobu.today_affection_gain = 5
    dobu.last_train_date = "2020-01-01"  # 過去の日付
    manager.save_dobumon(dobu)

    # train_menu を呼び出すとリセットされるはず
    # (内部的に日付チェックが走るため)
    success, result = manager.train_menu(dobu.dobumon_id, "massage")

    assert success is True
    updated = manager.get_dobumon(dobu.dobumon_id)
    assert updated.today_train_count == 0  # お昼寝はカウントされない
    assert updated.today_wild_battle_count == 0
    assert updated.today_affection_gain == 2  # マッサージは+2に強化された
    assert updated.last_train_date != "2020-01-01"


def test_lifespan_consumption_training(tmp_path):
    """トレーニング時の寿命消費検証"""
    db_path = str(tmp_path / "test_train_cons.db")
    sql_handler.init_db(db_path)
    repo = SQLiteDobumonRepository(db_path)
    manager = DobumonManager(repo)

    dobu = manager.create_dobumon(owner_id=123, name="訓練ドブ")
    dobu.lifespan = 100

    dobu.max_lifespan = 100.0
    manager.save_dobumon(dobu)

    # 1-5回目は安全圏（消費0）
    for _ in range(5):
        manager.train_menu(dobu.dobumon_id, "strength")

    updated = manager.get_dobumon(dobu.dobumon_id)
    assert updated.lifespan == 100  # 消費なし

    # 6回目以降は確率消費
    # 確実に減るまで繰り返す（確率は15%+、試行回数を稼ぐ）
    lost = False
    for _ in range(50):
        manager.train_menu(dobu.dobumon_id, "strength")
        curr = manager.get_dobumon(dobu.dobumon_id)
        if curr.lifespan < 100:
            lost = True
            break
    assert lost is True


def test_natural_aging_and_sudden_death(tmp_path, monkeypatch):
    """自然加齢と突然死の検証"""
    # テスト時のみ死亡を有効化
    monkeypatch.setattr("logic.dobumon.core.dob_manager.DISABLE_DEATH", False)

    db_path = str(tmp_path / "test_aging.db")
    sql_handler.init_db(db_path)
    repo = SQLiteDobumonRepository(db_path)
    manager = DobumonManager(repo)

    # 1. 通常の加齢
    dobu1 = manager.create_dobumon(owner_id=1, name="長生きドブ")
    dobu1.lifespan = 50

    dobu1.max_lifespan = 100.0
    manager.save_dobumon(dobu1)

    # 2. 晩年期の個体（突然死リスクあり）
    dobu2 = manager.create_dobumon(owner_id=2, name="風前の灯火")
    dobu2.lifespan = 5  # 晩年期
    manager.save_dobumon(dobu2)

    # 何度か加齢処理を実行して挙動を確認
    results = manager.process_natural_aging()
    assert results["affected"] >= 2

    updated1 = manager.get_dobumon(dobu1.dobumon_id)
    # 50 - (1.0 * 0.7) = 49.3
    assert updated1.lifespan == pytest.approx(49.3)

    # 突然死が起きるまでループ（または寿命が尽きるまで）
    death_occured = False
    for _ in range(10):
        res = manager.process_natural_aging()
        if res["deaths"] > 0:
            death_occured = True

        # 全滅チェック
        d1 = manager.get_dobumon(dobu1.dobumon_id)
        d2 = manager.get_dobumon(dobu2.dobumon_id)
        if not d1.is_alive or not d2.is_alive:
            death_occured = True
            break

    assert death_occured is True
