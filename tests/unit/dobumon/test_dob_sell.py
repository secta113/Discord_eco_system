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
    # 新ロジック:
    # base(5000) + stat_bonus(sqrt(500)*1000=22360) + gen_bonus(2000) + aff(0) = 29360
    # stage_mult(young=0.8) -> 29360 * 0.8 = 23488
    price = service.calculate_sell_price(dobu)
    assert price == 23488


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
    # 新ロジック:
    # base(5000) + stat_bonus(22360) + gen_bonus(1*500 + sqrt(2)*2000=3328) + aff(50*50=2500) = 33188
    # stage_mult(young=0.8) -> 33188 * 0.8 = 26550
    price = service.calculate_sell_price(dobu)
    assert price == 26550


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
    # ベース(before taboo): 23488
    # 禁忌深度2: 30%減額 (1層15%)
    # 23488 * 0.7 = 16441
    price = service.calculate_sell_price(dobu)
    assert price == 16441


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
    # 禁忌深度10以上 -> 90%減額
    # 23488 * 0.1 = 2348
    assert price == 2348


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
