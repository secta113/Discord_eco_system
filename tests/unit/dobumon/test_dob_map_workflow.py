from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from cogs.dobumon import DobumonCog
from logic.dobumon.core.dob_models import Dobumon


@pytest.fixture
def mock_bot():
    return MagicMock()


@pytest.fixture
def mock_manager():
    manager = MagicMock()
    return manager


@pytest.fixture
def cog(mock_bot, mock_manager):
    # 背景タスク（aging_task）が __init__ で開始される際、イベントループがないとエラーになるため
    # 一時的にディスクリプタをモックに差し替えて初期化します。
    original_task = DobumonCog.aging_task
    DobumonCog.aging_task = MagicMock()

    cog = DobumonCog(mock_bot)
    cog.manager = mock_manager

    # モックを戻します
    DobumonCog.aging_task = original_task
    return cog


@pytest.mark.asyncio
async def test_map_command_no_target_alive_only(cog, mock_manager):
    """引数なしの場合、生存個体のみが選択肢に表示されることを検証"""
    d1 = Dobumon(
        dobumon_id="d1",
        owner_id=1,
        name="Alive",
        is_alive=True,
        lineage=[],
        attribute="fire",
        generation=1,
        gender="M",
        hp=100,
        atk=50,
        defense=50,
        eva=50,
        spd=50,
        max_lifespan=100,
        lifespan=90,
    )
    d2 = Dobumon(
        dobumon_id="d2",
        owner_id=1,
        name="Dead",
        is_alive=False,
        lineage=[],
        attribute="water",
        generation=1,
        gender="F",
        hp=100,
        atk=50,
        defense=50,
        eva=50,
        spd=50,
        max_lifespan=100,
        lifespan=0,
    )
    mock_manager.get_user_dobumons.return_value = [d1, d2]

    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user.id = 1
    interaction.followup = AsyncMock()

    # コマンド実行
    await cog.map.callback(cog, interaction, target=None)

    # 検証: view.display_dobumons に d1 (生存) のみが含まれているか
    args, kwargs = interaction.followup.send.call_args
    view = kwargs.get("view")
    assert view is not None
    assert len(view.display_dobumons) == 1
    assert view.display_dobumons[0].dobumon_id == "d1"


@pytest.mark.asyncio
async def test_map_command_with_target_all_matching(cog, mock_manager):
    """名前指定がある場合、生存・死亡を問わず一致する全個体が表示されることを検証"""
    d1 = Dobumon(
        dobumon_id="d1",
        owner_id=1,
        name="Pochi",
        is_alive=True,
        lineage=[],
        attribute="fire",
        generation=2,
        gender="M",
        hp=100,
        atk=50,
        defense=50,
        eva=50,
        spd=50,
        max_lifespan=100,
        lifespan=50,
    )
    d2 = Dobumon(
        dobumon_id="d2",
        owner_id=1,
        name="Pochi",
        is_alive=False,
        lineage=[],
        attribute="water",
        generation=1,
        gender="F",
        hp=100,
        atk=50,
        defense=50,
        eva=50,
        spd=50,
        max_lifespan=100,
        lifespan=0,
    )
    d3 = Dobumon(
        dobumon_id="d3",
        owner_id=1,
        name="Other",
        is_alive=True,
        lineage=[],
        attribute="grass",
        generation=1,
        gender="M",
        hp=100,
        atk=50,
        defense=50,
        eva=50,
        spd=50,
        max_lifespan=100,
        lifespan=50,
    )
    mock_manager.get_user_dobumons.return_value = [d1, d2, d3]

    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user.id = 1
    interaction.followup = AsyncMock()

    # コmaンド実行 (target="Pochi")
    await cog.map.callback(cog, interaction, target="Pochi")

    # 検証: view.display_dobumons に d1 と d2 (名前一致) が含まれているか
    args, kwargs = interaction.followup.send.call_args
    view = kwargs.get("view")
    assert view is not None
    assert len(view.display_dobumons) == 2
    ids = [d.dobumon_id for d in view.display_dobumons]
    assert "d1" in ids
    assert "d2" in ids
    assert "d3" not in ids
