from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from cogs.system import System


@pytest.mark.asyncio
async def test_cmd_user_id(init_test_env, mock_interaction):
    """Context Menu 'User ID' のテスト"""
    # System Cogは初期化時にモックのbotを必要とする
    bot = MagicMock()
    # bot.tree.add_command が呼ばれるが無視
    cog = System(bot)

    target = MagicMock(spec=discord.Member)
    target.id = 55667788
    target.display_name = "TargetGuy"

    await cog.get_user_id(interaction=mock_interaction, member=target)

    mock_interaction.response.send_message.assert_called_once()
    assert "55667788" in mock_interaction.response.send_message.call_args[0][0]
