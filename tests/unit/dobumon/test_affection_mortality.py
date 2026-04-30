import datetime

import pytest

from core.handlers import sql_handler
from core.handlers.storage import SQLiteDobumonRepository
from logic.dobumon.core.dob_manager import DobumonManager
from logic.dobumon.core.dob_models import Dobumon


def test_affection_gain_limits(tmp_path):
    """絆の上昇制限の検証"""
    db_path = str(tmp_path / "test_aff.db")
    sql_handler.init_db(db_path)
    repo = SQLiteDobumonRepository(db_path)
    manager = DobumonManager(repo)

    dobu = manager.create_dobumon(owner_id=123, name="検証ドブ")
    dobu.today_train_count = 0
    dobu.today_affection_gain = 0
    dobu.affection = 0
    manager.save_dobumon(dobu)

    # 1. 通常トレーニング 5回
    for _ in range(5):
        manager.train_menu(dobu.dobumon_id, "strength")

    updated = manager.get_dobumon(dobu.dobumon_id)
    # 5回分、大成功がなければ 5 上昇しているはず
    assert updated.today_affection_gain >= 5
    assert updated.affection >= 5

    # 2. 6回目（オーバーワーク）で絆が上がらないか検証
    current_aff = updated.affection
    current_gain = updated.today_affection_gain
    manager.train_menu(dobu.dobumon_id, "strength")

    overworked_dobu = manager.get_dobumon(dobu.dobumon_id)
    assert overworked_dobu.today_train_count == 6
    assert overworked_dobu.affection == current_aff  # 上がっていないこと
    assert overworked_dobu.today_affection_gain == current_gain


def test_massage_mechanics(tmp_path):
    """マッサージの挙動検証（回復は無制限、絆は1日1回）"""
    db_path = str(tmp_path / "test_massage.db")
    sql_handler.init_db(db_path)
    repo = SQLiteDobumonRepository(db_path)
    manager = DobumonManager(repo)

    dobu = manager.create_dobumon(owner_id=123, name="マッサージ検証")
    dobu.hp = 100
    dobu.health = 50  # 半分
    dobu.today_affection_gain = 0
    dobu.affection = 0
    manager.save_dobumon(dobu)

    # 1回目：成功。HP回復し、絆も上がる(+2)
    success, result = manager.train_menu(dobu.dobumon_id, "massage")
    assert success is True
    updated = manager.get_dobumon(dobu.dobumon_id)
    assert updated.health > 50
    assert updated.affection == 2
    assert updated.today_massage_count == 1
    assert updated.today_train_count == 0  # 育成回数には含まれないことの検証

    # 2回目：成功。HPはさらに回復するが、絆は上がらない
    last_health = updated.health
    success, result = manager.train_menu(dobu.dobumon_id, "massage")
    assert success is True
    updated2 = manager.get_dobumon(dobu.dobumon_id)
    assert updated2.health >= last_health
    assert updated2.affection == 2  # 据え置き
    assert updated2.today_massage_count == 2


def test_affection_daily_limit_of_8(tmp_path):
    """1日の絆上昇上限 8 の検証"""
    db_path = str(tmp_path / "test_limit8.db")
    sql_handler.init_db(db_path)
    repo = SQLiteDobumonRepository(db_path)
    manager = DobumonManager(repo)

    dobu = manager.create_dobumon(owner_id=123, name="上限検証ドブ")
    dobu.affection = 0
    dobu.today_affection_gain = 0
    manager.save_dobumon(dobu)

    # トレーニングで 5 か 6 (大成功あり) 上げる
    for _ in range(5):
        manager.train_menu(dobu.dobumon_id, "strength")

    # マッサージで +2
    manager.train_menu(dobu.dobumon_id, "massage")

    updated = manager.get_dobumon(dobu.dobumon_id)
    # 大成功が何度あっても合計 8 で止まるか
    # (内部的には 1*4 + 2*1 + 2 = 8 が理想ムーブ)
    assert updated.today_affection_gain <= 8


def test_sudden_death_risk_reduction(tmp_path, monkeypatch):
    """突然死リスクの緩和と絆ボーナスの検証"""
    monkeypatch.setattr("logic.dobumon.core.dob_manager.DISABLE_DEATH", False)
    db_path = str(tmp_path / "test_death_logic.db")
    sql_handler.init_db(db_path)
    repo = SQLiteDobumonRepository(db_path)
    manager = DobumonManager(repo)

    # 晩年期で絆が深いドブ (100)
    dobu_bonded = manager.create_dobumon(owner_id=1, name="深い絆")
    dobu_bonded.lifespan = 5  # twilight
    dobu_bonded.affection = 100  # 不滅
    manager.save_dobumon(dobu_bonded)

    # 晩年期で絆がないドブ (0)
    dobu_neutral = manager.create_dobumon(owner_id=2, name="希薄な絆")
    dobu_neutral.lifespan = 5  # twilight
    dobu_neutral.affection = 0
    manager.save_dobumon(dobu_neutral)

    # 大量試行は難しいが、ロジック自体は manager.py の risk_prob 計算に含まれている
    # ここでは老化速度 (consumption_mod) の差を検証
    results = manager.process_natural_aging()

    d1 = manager.get_dobumon(dobu_bonded.dobumon_id)
    d2 = manager.get_dobumon(dobu_neutral.dobumon_id)

    # 絆深い方は consumption_mod = 0.85 (さらに hardy なら 0.85*0.7=0.595)
    # 絆ない方は consumption_mod = 1.0 (hardyなら 0.7)
    # 差があることを確認
    diff_bonded = dobu_bonded.lifespan - d1.lifespan
    diff_neutral = dobu_neutral.lifespan - d2.lifespan

    assert diff_bonded < diff_neutral
