from unittest.mock import MagicMock, patch

import pytest

from logic.dobumon.core.dob_factory import DobumonFactory
from logic.dobumon.core.dob_manager import DobumonManager


def test_dobumon_factory_explicit_creation():
    """性別と属性を明示的に指定した生成テスト"""
    owner_id = 999
    name = "TestDobu"

    # オス、火属性
    dobu_m_fire = DobumonFactory.create_new(owner_id, name, gender="M", attribute="fire")
    assert dobu_m_fire.gender == "M"
    assert dobu_m_fire.attribute == "fire"
    assert dobu_m_fire.name == name

    # メス、草属性
    dobu_f_grass = DobumonFactory.create_new(owner_id, name, gender="F", attribute="grass")
    assert dobu_f_grass.gender == "F"
    assert dobu_f_grass.attribute == "grass"
    assert dobu_f_grass.name == name


def test_dobumon_manager_create_pass_through():
    """Manager 経由での指定値渡しテスト"""
    repo = MagicMock()
    manager = DobumonManager(repo)

    with patch("logic.dobumon.core.dob_factory.DobumonFactory.create_new") as mock_create:
        manager.create_dobumon(1, "Test", gender="F", attribute="water")
        mock_create.assert_called_with(1, "Test", "buyer", "F", "water")


@pytest.mark.asyncio
async def test_dob_buy_view_logic_flow():
    """DobumonBuyView のロジックフローをモックでシミュレーション"""
    from unittest.mock import AsyncMock

    from logic.dobumon.core.dob_exceptions import DobumonInsufficientPointsError
    from logic.dobumon.dob_views.dob_buy import DobumonBuyView

    user = MagicMock()
    user.id = 123
    manager = MagicMock()
    buy_service = MagicMock()
    buy_service.manager = manager

    view = DobumonBuyView(user, buy_service)
    view.gender = "M"
    view.attribute = "fire"

    interaction = MagicMock()
    interaction.user.id = 123
    interaction.response.edit_message = AsyncMock()
    interaction.edit_original_response = AsyncMock()
    interaction.followup.send = AsyncMock()

    # 正常系
    real_dobu = DobumonFactory.create_new(123, "SuccessName", gender="M", attribute="fire")
    buy_service.execute_purchase = AsyncMock(return_value=real_dobu)
    buy_service.get_shop_config.return_value = {
        "name": "TestShop",
        "emoji": "🥚",
        "color": 0x000000,
    }
    view.shop_id = "mart"
    view.preview_data = {"iv": real_dobu.iv, "has_mutation": False, "shop_id": "mart"}

    # 正常系実行
    await view.process_purchase(interaction, "SuccessName")

    # buy_service が呼ばれていること
    buy_service.execute_purchase.assert_called_once_with(
        user_id=123,
        name="SuccessName",
        gender="M",
        attribute="fire",
        preview_data=view.preview_data,
    )
    # インラクションが正常に終了していること
    interaction.edit_original_response.assert_called_once()
