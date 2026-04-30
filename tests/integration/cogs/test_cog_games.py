from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from cogs.games import Games
from core.economy import wallet
from managers.manager import game_manager


@pytest.fixture
def cog_games():
    bot = MagicMock()
    return Games(bot)


@pytest.mark.asyncio
async def test_cmd_blackjack_recruit(init_test_env, mock_interaction, cog_games):
    """/dd-game blackjack の募集開始テスト"""
    # スタック設定
    wallet.save_balance(mock_interaction.user.id, 1000)

    await cog_games.blackjack.callback(cog_games, interaction=mock_interaction, bet=100)

    mock_interaction.followup.send.assert_called_once()
    args, kwargs = mock_interaction.followup.send.call_args
    embed = kwargs.get("embed") or args[0]
    assert "ブラックジャック 参加者募集" in embed.title
    assert "100 pts" in embed.fields[1].value


@pytest.mark.asyncio
async def test_cmd_chinchiro_recruit(init_test_env, mock_interaction, cog_games):
    """/dd-game chinchiro の募集開始テスト"""
    wallet.save_balance(mock_interaction.user.id, 1000)

    await cog_games.chinchiro.callback(cog_games, interaction=mock_interaction, bet=500)

    mock_interaction.followup.send.assert_called_once()
    embed = mock_interaction.followup.send.call_args[1].get("embed")
    assert "チンチロリン 参加者募集" in embed.title
    assert "500 pts" in embed.fields[1].value


@pytest.mark.asyncio
async def test_cmd_poker_recruit(init_test_env, mock_interaction, cog_games):
    """/dd-game poker の募集開始テスト"""
    wallet.save_balance(mock_interaction.user.id, 5000)

    await cog_games.poker.callback(
        cog_games, interaction=mock_interaction, bet=200, buyin=4000, players=4
    )

    mock_interaction.followup.send.assert_called_once()
    embed = mock_interaction.followup.send.call_args[1].get("embed")
    assert "テキサス・ホールデム 参加者募集" in embed.title
    # BBが200であることを確認
    assert "200 pts" in embed.fields[2].value


@pytest.mark.asyncio
async def test_cmd_gacha(init_test_env, mock_interaction, cog_games):
    """/dd-game gacha のテスト"""
    # 充分な残高
    user_id = mock_interaction.user.id
    wallet.save_balance(user_id, 10000)
    wallet.set_gacha_count(user_id, 0)
    # 確実に日付も過去にしておく
    wallet.set_last_gacha_daily(user_id, "1970-01-01")

    await cog_games.gacha.callback(cog_games, interaction=mock_interaction)

    mock_interaction.followup.send.assert_called_once()
    args, kwargs = mock_interaction.followup.send.call_args
    embed = kwargs.get("embed") or args[0]
    assert "ガチャ結果" in embed.title


@pytest.mark.asyncio
async def test_cmd_cancel_recruit(init_test_env, mock_interaction, cog_games):
    """/dd-cancel (募集中) のテスト"""
    user_id = mock_interaction.user.id
    wallet.save_balance(user_id, 1000)

    # まず募集を作成
    game_manager.create_blackjack(mock_interaction.channel_id, mock_interaction.user, 100)

    await cog_games.cancel_game_unified.callback(
        cog_games, interaction=mock_interaction, force=False
    )

    # セッションが終了していること
    assert game_manager.get_session(mock_interaction.channel_id) is None
    mock_interaction.response.send_message.assert_called_once()
    assert "キャンセル" in mock_interaction.response.send_message.call_args[0][0]


@pytest.mark.asyncio
async def test_cmd_poker_rule(init_test_env, mock_interaction, cog_games):
    """/dd-game poker_rule のテスト"""
    await cog_games.poker_rule.callback(cog_games, interaction=mock_interaction)
    mock_interaction.followup.send.assert_called_once()
    embed = mock_interaction.followup.send.call_args[1].get("embed")
    assert "Texas Hold'em Poker - 究極ガイド" in embed.title


@pytest.mark.asyncio
async def test_cmd_match_recruit(init_test_env, mock_interaction, cog_games):
    """/dd-game match のテスト"""
    wallet.save_balance(mock_interaction.user.id, 1000)
    await cog_games.match.callback(cog_games, interaction=mock_interaction, bet=300)
    mock_interaction.followup.send.assert_called_once()
    embed = mock_interaction.followup.send.call_args[1].get("embed")
    assert "外部マッチ 募集" in embed.title
