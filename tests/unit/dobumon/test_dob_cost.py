from unittest.mock import AsyncMock, MagicMock

import pytest

from core.economy import wallet
from core.handlers.storage import SQLiteDobumonRepository
from logic.dobumon.core.dob_manager import DobumonManager
from logic.dobumon.core.dob_training_service import DobumonTrainingService


@pytest.fixture
def dobumon_service(test_db_path):
    repo = SQLiteDobumonRepository(test_db_path)
    manager = DobumonManager(repo)
    return DobumonTrainingService(manager)


@pytest.mark.asyncio
async def test_training_step_up_cost(dobumon_service, mock_interaction):
    """育成回数に応じてコストが段階的に増加することを検証"""
    user_id = mock_interaction.user.id
    wallet.save_balance(user_id, 100000)

    # テスト用ドブモン作成
    manager = dobumon_service.manager
    dobu = manager.create_dobumon(user_id, "コスト検証丸")
    manager.save_dobumon(dobu)
    dobumon_id = dobu.dobumon_id

    # 1回目: 500 pts
    initial_balance = wallet.load_balance(user_id)
    await dobumon_service.execute_training(mock_interaction, dobumon_id, "strength")
    balance_after_1 = wallet.load_balance(user_id)
    assert initial_balance - balance_after_1 == 500

    # 2回目: 1000 pts (なつき度による極小割引を防ぐためリセット)
    dobu = manager.get_dobumon(dobumon_id)
    dobu.affection = 0
    manager.save_dobumon(dobu)
    await dobumon_service.execute_training(mock_interaction, dobumon_id, "strength")
    balance_after_2 = wallet.load_balance(user_id)
    assert balance_after_1 - balance_after_2 == 1000

    # 3回目: 2000 pts
    dobu = manager.get_dobumon(dobumon_id)
    dobu.affection = 0
    manager.save_dobumon(dobu)
    await dobumon_service.execute_training(mock_interaction, dobumon_id, "strength")
    balance_after_3 = wallet.load_balance(user_id)
    assert balance_after_2 - balance_after_3 == 2000

    # 4回目: 4000 pts
    dobu = manager.get_dobumon(dobumon_id)
    dobu.affection = 0
    manager.save_dobumon(dobu)
    await dobumon_service.execute_training(mock_interaction, dobumon_id, "strength")
    balance_after_4 = wallet.load_balance(user_id)
    assert balance_after_3 - balance_after_4 == 4000


@pytest.mark.asyncio
async def test_training_affection_discount(dobumon_service, mock_interaction):
    """なつき度に応じて割引が適用されることを検証"""
    user_id = mock_interaction.user.id
    wallet.save_balance(user_id, 100000)

    manager = dobumon_service.manager
    dobu = manager.create_dobumon(user_id, "割引検証丸")
    manager.save_dobumon(dobu)
    dobumon_id = dobu.dobumon_id

    # なつき度 100 (10%割引)
    dobu.affection = 100
    manager.save_dobumon(dobu)

    initial_balance = wallet.load_balance(user_id)
    await dobumon_service.execute_training(mock_interaction, dobumon_id, "strength")
    # 初回 500 * (1 - 0.1) = 450
    assert initial_balance - wallet.load_balance(user_id) == 450

    # なつき度 500 (50%割引 - 最大)
    dobu = manager.get_dobumon(dobumon_id)
    dobu.affection = 500
    dobu.today_train_count = 0  # 日を跨いだと仮定して1回目にリセット
    manager.save_dobumon(dobu)

    current_balance = wallet.load_balance(user_id)
    await dobumon_service.execute_training(mock_interaction, dobumon_id, "strength")
    # 1回目 500 * (1 - 0.5) = 250
    assert current_balance - wallet.load_balance(user_id) == 250

    # なつき度 1000 (上限50%割引の確認)
    dobu = manager.get_dobumon(dobumon_id)
    dobu.affection = 1000
    dobu.today_train_count = 0
    manager.save_dobumon(dobu)

    current_balance = wallet.load_balance(user_id)
    await dobumon_service.execute_training(mock_interaction, dobumon_id, "strength")
    # 1回目 500 * (1 - 0.5) = 250 (60%にはならない)
    assert current_balance - wallet.load_balance(user_id) == 250
