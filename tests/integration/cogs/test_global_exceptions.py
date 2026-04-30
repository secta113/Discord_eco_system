from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
import pytest_asyncio
from discord import app_commands

from cogs.system import setup
from core.utils.exceptions import EconomyError
from logic.dobumon.core.dob_exceptions import DobumonError
from logic.poker.pk_exceptions import PokerError


@pytest_asyncio.fixture
async def system_cog_error_handler():
    """System Cogの on_app_command_error ハンドラを取得するお膳立て"""
    bot = MagicMock(spec=discord.ext.commands.Bot)
    bot.tree = MagicMock()
    # 登録されるエラーハンドラを横取りする
    error_handler_ref = [None]

    def catch_error_handler(func):
        error_handler_ref[0] = func
        return func

    bot.tree.error = catch_error_handler

    await setup(bot)

    handler = error_handler_ref[0]
    assert handler is not None, "Error handler was not registered."
    return handler


@pytest.mark.asyncio
async def test_dobumon_error_global_formatting(system_cog_error_handler, mock_interaction):
    handler = system_cog_error_handler
    mock_interaction.response.is_done.return_value = False

    # オリジナルのエラーがDobumonErrorとしてラップされたAppCommandErrorを生成
    orig_error = DobumonError("ドブモンが疲れています。")
    app_error = app_commands.AppCommandError("Command execution failed")
    app_error.original = orig_error

    await handler(mock_interaction, app_error)

    # 適切に DobumonFormatter.format_error_embed 経由で send_message が呼ばれることを確認
    mock_interaction.response.send_message.assert_called_once()
    _, kwargs = mock_interaction.response.send_message.call_args
    assert "embed" in kwargs
    embed = kwargs["embed"]
    # DobumonErrorは特定のテーマカラーなどでフォーマットされるはず
    assert embed.description == "ドブモンが疲れています。"
    assert embed.title is not None
    # 共通して送られる ephemeral 設定
    assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_poker_error_global_formatting(system_cog_error_handler, mock_interaction):
    handler = system_cog_error_handler
    mock_interaction.response.is_done.return_value = False

    orig_error = PokerError("ベット額が不足しています。")
    app_error = app_commands.AppCommandError("Command execution failed")
    app_error.original = orig_error

    await handler(mock_interaction, app_error)

    mock_interaction.response.send_message.assert_called_once()
    _, kwargs = mock_interaction.response.send_message.call_args
    embed = kwargs["embed"]
    assert "ベット額が不足しています。" in embed.description
    assert (
        "🃏" in str(embed.title)
        or "Poker" in str(getattr(embed.author, "name", ""))
        or getattr(embed, "title", None) is not None
    )


@pytest.mark.asyncio
async def test_fallback_unexpected_error(system_cog_error_handler, mock_interaction):
    handler = system_cog_error_handler
    mock_interaction.response.is_done.return_value = False

    # 未知のランタイムエラー
    orig_error = ValueError("This shouldn't happen")
    app_error = app_commands.AppCommandError("Command execution failed")
    app_error.original = orig_error

    await handler(mock_interaction, app_error)

    # 完全に予期せぬエラーは一律で「予期せぬエラーが発生しました…」の文字列になる
    mock_interaction.response.send_message.assert_called_once()
    args, kwargs = mock_interaction.response.send_message.call_args
    assert "予期せぬエラーが発生しました" in kwargs.get("content", args[0] if args else "")
    assert kwargs.get("ephemeral") is True
