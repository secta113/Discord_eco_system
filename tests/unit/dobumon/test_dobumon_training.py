import os

import pytest

from core.handlers import sql_handler
from core.handlers.storage import SQLiteDobumonRepository
from logic.dobumon.core.dob_manager import DobumonManager


def test_training_stat_increase(tmp_path):
    """トレーニングによるステータス上昇のテスト"""
    db_path = str(tmp_path / "test.db")
    sql_handler.init_db(db_path)
    repo = SQLiteDobumonRepository(db_path)
    manager = DobumonManager(repo)

    # IV = 1.0 の個体を作成
    dobu = manager.create_dobumon(owner_id=123, name="鍛練丸")
    dobu.iv = {"hp": 1.0, "atk": 1.0, "defense": 1.0, "eva": 1.0, "spd": 1.0}
    manager.save_dobumon(dobu)

    initial_atk = dobu.atk
    # トレーニング開始
    manager.train_menu(dobu.dobumon_id, "strength")

    updated_dobu = manager.get_dobumon(dobu.dobumon_id)
    assert updated_dobu.atk > initial_atk


from unittest.mock import patch


def test_overtraining_risk(tmp_path):
    """オーバーワーク（寿命減少）のリスクテスト"""
    db_path = str(tmp_path / "test.db")
    sql_handler.init_db(db_path)
    repo = SQLiteDobumonRepository(db_path)
    manager = DobumonManager(repo)

    dobu = manager.create_dobumon(owner_id=123, name="限界突破")
    manager.save_dobumon(dobu)

    # 5回目まではリスクが低い（通常 15% の加算がない）
    # 6回目以降、確率で寿命が減る。確実に減らすために random.random を 0 に固定する。
    with patch("logic.dobumon.training.dob_train.random.random", return_value=0.0):
        # 1回目からリスク（1%程度）はあるが、オーバーワーク状態（6回目以降）を明示的にテスト
        for _ in range(5):
            manager.train_menu(dobu.dobumon_id, "strength")

        initial_lifespan = manager.get_dobumon(dobu.dobumon_id).lifespan

        # 6回目
        manager.train_menu(dobu.dobumon_id, "strength")

        final_lifespan = manager.get_dobumon(dobu.dobumon_id).lifespan
        assert final_lifespan < initial_lifespan
