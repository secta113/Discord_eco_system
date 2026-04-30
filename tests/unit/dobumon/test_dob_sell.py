from unittest.mock import MagicMock, patch

import pytest

from logic.dobumon.core.dob_manager import DobumonManager
from logic.dobumon.core.dob_market_service import DobumonMarketService
from logic.dobumon.core.dob_models import Dobumon


@pytest.fixture
def mock_manager():
    return MagicMock(spec=DobumonManager)


@pytest.fixture
def service(mock_manager):
    return DobumonMarketService(mock_manager)


def test_calculate_sell_price_basic(service):
    # 基本構成: 第1世代, 懐き度0, ステータス合計 500 (100x5), 禁忌深度0
    dobu = Dobumon(
        dobumon_id="test_id",
        owner_id=123,
        name="Test",
        gender="M",
        hp=100,
        atk=100,
        defense=100,
        eva=100,
        spd=100,
        generation=1,
        affection=0,
        genetics={"forbidden_depth": 0},
    )
    # 10,000 + (500 * 5) + 0 + 0 = 12,500
    price = service.calculate_sell_price(dobu)
    assert price == 12500


def test_calculate_sell_price_with_bonus(service):
    # ボーナスあり: 第2世代, 懐き度50, ステータス合計 500, 禁忌深度0
    dobu = Dobumon(
        dobumon_id="test_id",
        owner_id=123,
        name="Test",
        gender="M",
        hp=100,
        atk=100,
        defense=100,
        eva=100,
        spd=100,
        generation=2,
        affection=50,
        genetics={"forbidden_depth": 0},
    )
    # 10,000 + (500 * 5) + (50 * 50) + (1 * 2,000)
    # 10,000 + 2,500 + 2,500 + 2,000 = 17,000
    price = service.calculate_sell_price(dobu)
    assert price == 17000


def test_calculate_sell_price_with_taboo(service):
    # 禁忌深度あり: 第1世代, 懐き度0, ステータス合計 500, 禁忌深度2
    dobu = Dobumon(
        dobumon_id="test_id",
        owner_id=123,
        name="Test",
        gender="M",
        hp=100,
        atk=100,
        defense=100,
        eva=100,
        spd=100,
        generation=1,
        affection=0,
        genetics={"forbidden_depth": 2},
    )
    # ベース: 12,500
    # 20%減額 (-2,500) = 10,000
    price = service.calculate_sell_price(dobu)
    assert price == 10000


def test_calculate_sell_price_max_taboo(service):
    # 禁忌深度10以上
    dobu = Dobumon(
        dobumon_id="test_id",
        owner_id=123,
        name="Test",
        gender="M",
        hp=100,
        atk=100,
        defense=100,
        eva=100,
        spd=100,
        generation=1,
        affection=0,
        genetics={"forbidden_depth": 10},
    )
    price = service.calculate_sell_price(dobu)
    assert price == 0


@pytest.mark.asyncio
async def test_execute_sell(service, mock_manager):
    from unittest.mock import AsyncMock

    mock_interaction = MagicMock()
    mock_interaction.user.id = 123
    mock_interaction.response.is_done.return_value = False
    mock_interaction.response.send_message = AsyncMock()
    mock_interaction.edit_original_response = AsyncMock()
    mock_interaction.followup.send = AsyncMock()

    dobu = Dobumon(
        dobumon_id="test_id",
        owner_id=123,
        name="Test",
        gender="M",
        hp=100,
        atk=100,
        defense=100,
        eva=100,
        spd=100,
        is_alive=True,
    )
    mock_manager.get_dobumon.return_value = dobu

    with (
        patch("core.economy.wallet.load_balance", return_value=1000),
        patch("core.economy.wallet.save_balance") as mock_save,
        patch("core.economy.wallet.add_history") as mock_hist,
    ):
        await service.execute_sell(mock_interaction, "test_id")

        # 物理削除ではなく、状態を更新して保存することを確認
        mock_manager.save_dobumon.assert_called_once()
        saved_dobu = mock_manager.save_dobumon.call_args[0][0]
        assert saved_dobu.is_sold is True
        assert saved_dobu.is_alive is False

        mock_save.assert_called_once()
        mock_hist.assert_called_once()
        mock_interaction.response.send_message.assert_called_once()
