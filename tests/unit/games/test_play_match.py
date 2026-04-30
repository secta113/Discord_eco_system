from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from cogs.games import Games
from core.economy import wallet
from logic.match_view import MatchJoinView, MatchResultSelect
from managers.manager import game_manager


@pytest.fixture
def cog_games():
    bot = MagicMock()
    return Games(bot)


def create_mock_interaction(user_id, name):
    interaction = MagicMock(spec=discord.Interaction)
    interaction.response = MagicMock()
    interaction.response.send_message = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.response.edit_message = AsyncMock()
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock(return_value=MagicMock(spec=discord.Message))
    interaction.edit_original_response = AsyncMock()
    interaction.channel = MagicMock()
    interaction.channel.send = AsyncMock()

    interaction.user = MagicMock(spec=discord.Member)
    interaction.user.id = user_id
    interaction.user.display_name = name
    interaction.user.mention = f"<@{user_id}>"

    interaction.guild = MagicMock()
    interaction.guild.id = 888222333
    interaction.guild.get_member = MagicMock(return_value=interaction.user)

    # Generate unique channel ID to avoid collisions
    interaction.channel_id = 999111222 + (user_id % 100000)
    interaction.guild_id = 888222333
    return interaction


@pytest.mark.asyncio
async def test_play_match_full_flow(init_test_env, mock_button, cog_games):
    """Matchの募集 -> 参加 -> 結果報告 -> 勝者選択 -> 精算の流れ"""
    # Force unique ID for host to avoid any collision
    host_id = 411100000 + (id(cog_games) % 20000)
    player_id = 522200000 + (id(cog_games) % 20000)
    wallet.save_balance(host_id, 40000)
    wallet.save_balance(player_id, 40000)

    host_interaction = create_mock_interaction(host_id, "HostUser")

    # 1. 募集 (Host is added in create_match)
    cmd = cog_games.match
    func = cmd.callback if hasattr(cmd, "callback") else cmd
    await func(cog_games, interaction=host_interaction, bet=100)

    # 2. プレイヤー参加
    player_interaction = create_mock_interaction(player_id, "PlayerUser")
    player_interaction.channel_id = host_interaction.channel_id

    msg = game_manager.join_session(host_interaction.channel_id, player_interaction.user)
    assert msg  # 成功メッセージが返ることを確認

    # 3. 決済準備 (RE-FETCH session to get correct pot/players after join_session)
    session = game_manager.get_session(host_interaction.channel_id)
    assert len(session.players) == 2
    assert session.pot == 200

    # 4. 勝者確定
    mr_select = MatchResultSelect(session, game_manager)

    mock_view = MagicMock()
    mock_view.original_message = MagicMock()
    mock_view.original_message.edit = AsyncMock()
    mock_view.original_view = MagicMock()
    mock_view.original_view.children = []
    mock_view.children = [mr_select]

    with patch.object(MatchResultSelect, "values", new=[str(host_id)]):
        with patch.object(MatchResultSelect, "view", new=mock_view):
            await MatchResultSelect.callback(mr_select, interaction=host_interaction)

    # 5. 精算確認
    assert game_manager.get_session(host_interaction.channel_id) is None
    # 39900 + 200*1.05 = 39900 + 210 = 40110
    final_balance = wallet.load_balance(host_id)
    assert final_balance > 40000
    assert wallet.load_balance(player_id) == 39900
