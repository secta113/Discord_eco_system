from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from cogs.admin import Admin
from core.economy import wallet


@pytest.mark.asyncio
async def test_cmd_logs(init_test_env, mock_interaction):
    """/dd-mod logs のテスト"""
    bot = MagicMock()
    cog = Admin(bot)

    target = MagicMock(spec=discord.Member)
    target.id = 11112222
    target.display_name = "TargetMember"

    wallet.save_balance(target.id, 0)
    wallet.add_history(target.id, "Test History", 100)

    await cog.logs.callback(cog, interaction=mock_interaction, target=target)

    mock_interaction.response.send_message.assert_called_once()
    args, kwargs = mock_interaction.response.send_message.call_args
    embed = kwargs.get("embed") or args[0]
    assert "TargetMember の履歴" in embed.title
    assert "Test History" in embed.description


@pytest.mark.asyncio
async def test_cmd_status(init_test_env, mock_interaction):
    """/dd-mod status のテスト"""
    bot = MagicMock()
    bot.maintenance_mode = False
    cog = Admin(bot)

    # 既存ユーザーをクリア (conftestでリセットされるが念のため)
    for uid in list(wallet.get_all_balances().keys()):
        wallet.save_balance(int(uid), 0)

    wallet.save_balance(1, 1000)
    wallet.save_balance(2, 2000)

    await cog.status.callback(cog, interaction=mock_interaction)

    mock_interaction.response.send_message.assert_called_once()
    args, kwargs = mock_interaction.response.send_message.call_args
    embed = kwargs.get("embed") or args[0]
    # 3,000 pts (1000 + 2000)
    fields = {f.name: f.value for f in embed.fields}
    assert "3,000 pts" in fields["総流通ポイント"]


@pytest.mark.asyncio
async def test_cmd_maintenance(init_test_env, mock_interaction):
    """/dd-mod maintenance のテスト"""
    bot = MagicMock()
    bot.maintenance_mode = False
    cog = Admin(bot)

    await cog.maintenance.callback(cog, interaction=mock_interaction, state="on")
    assert bot.maintenance_mode is True

    await cog.maintenance.callback(cog, interaction=mock_interaction, state="off")
    assert bot.maintenance_mode is False


@pytest.mark.asyncio
async def test_cmd_status_all(init_test_env, mock_interaction):
    """/dd-mod status_all のテスト"""
    bot = MagicMock()
    cog = Admin(bot)

    # 既存データの仕込み
    wallet.save_balance(111, 10000)
    wallet.save_balance(222, 5000)

    await cog.status_all.callback(cog, interaction=mock_interaction)

    mock_interaction.response.send_message.assert_called_once()
    embed = mock_interaction.response.send_message.call_args[1].get("embed")
    assert "エコシステム全体統計" in embed.title
    assert "10,000 pts" in embed.description


@pytest.mark.asyncio
async def test_cmd_winner(init_test_env, mock_interaction):
    """/dd-mod winner のテスト"""
    bot = MagicMock()
    cog = Admin(bot)

    wallet.save_balance(333, 999999)
    wallet.update_stats(333, True, 100000)  # 1 win, max win 100k

    await cog.winner.callback(cog, interaction=mock_interaction)

    mock_interaction.response.send_message.assert_called_once()
    embed = mock_interaction.response.send_message.call_args[1].get("embed")
    assert "Hall of Fame" in embed.title
    assert "999,999 pts" in embed.fields[0].value
