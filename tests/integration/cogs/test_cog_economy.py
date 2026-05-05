from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from cogs.economy import Economy
from core.economy import wallet
from logic.economy.jackpot import JackpotService


@pytest.mark.asyncio
async def test_cmd_balance(init_test_env, mock_interaction):
    """/dd-wallet balance のテスト"""
    bot = MagicMock()
    cog = Economy(bot)

    # 残高設定
    user_id = mock_interaction.user.id
    wallet.save_balance(user_id, 5000)

    await cog.balance.callback(cog, interaction=mock_interaction)

    # レスポンスの検証 (defer_response により followup.send が呼ばれる)
    mock_interaction.followup.send.assert_called_once()
    args, kwargs = mock_interaction.followup.send.call_args
    assert "**5,000** pts" in args[0]


@pytest.mark.asyncio
async def test_cmd_jackpot(init_test_env, mock_interaction):
    """/dd-wallet jackpot のテスト"""
    bot = MagicMock()
    cog = Economy(bot)

    # ジャックポット設定
    JackpotService._save_pool(777777)

    await cog.jackpot.callback(cog, interaction=mock_interaction)

    mock_interaction.followup.send.assert_called_once()
    args, kwargs = mock_interaction.followup.send.call_args
    embed = kwargs.get("embed") or args[0]
    assert "**777,777** pts" in embed.description


@pytest.mark.asyncio
async def test_cmd_pay(init_test_env, mock_interaction):
    """/dd-wallet pay のテスト"""
    bot = MagicMock()
    cog = Economy(bot)

    target = MagicMock(spec=discord.Member)
    target.id = 987654321
    target.display_name = "TargetUser"
    target.mention = "<@987654321>"

    wallet.save_balance(mock_interaction.user.id, 1000)
    wallet.save_balance(target.id, 0)

    await cog.pay.callback(cog, interaction=mock_interaction, target=target, amount=500)

    assert wallet.load_balance(mock_interaction.user.id) == 500
    assert wallet.load_balance(target.id) == 500
    mock_interaction.followup.send.assert_called_once()
    assert target.mention in mock_interaction.followup.send.call_args[0][0]


@pytest.mark.asyncio
async def test_cmd_stats(init_test_env, mock_interaction):
    """/dd-wallet stats のテスト"""
    bot = MagicMock()
    cog = Economy(bot)

    user_id = 999999
    mock_interaction.user.id = user_id
    wallet.save_balance(user_id, 1234)
    wallet.update_stats(user_id, True, 1000)  # 1 win, max win 1000

    await cog.stats.callback(cog, interaction=mock_interaction)

    mock_interaction.followup.send.assert_called_once()
    args, kwargs = mock_interaction.followup.send.call_args
    embed = kwargs.get("embed") or args[0]
    # embed内のフィールドを確認
    fields = {f.name: f.value for f in embed.fields}
    assert "1,234 pts" in fields["所持ポイント"]

    current_wins = wallet.get_stats(user_id)["total_wins"]
    assert f"{current_wins} 回" in fields["累計勝利回数"]
