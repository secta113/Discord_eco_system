from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from cogs.games import Games
from core.economy import wallet
from core.ui.view_base import JoinView
from logic.poker.pk_view import PokerView
from managers.manager import game_manager


@pytest.fixture
def cog_games():
    bot = MagicMock()
    return Games(bot)


@pytest.mark.asyncio
async def test_play_poker_full_flow(init_test_env, mock_interaction, mock_button, cog_games):
    """Pokerの募集 -> 参加 -> 開始 -> アクション -> 決着までの流れをテスト"""
    user_id = mock_interaction.user.id
    wallet.save_balance(user_id, 10000)

    # 1. 募集
    cmd = cog_games.poker
    func = cmd.callback if hasattr(cmd, "callback") else cmd
    await func(cog_games, interaction=mock_interaction, bet=100, buyin=2000, players=2)

    # 2. 参加 (JoinView)
    args, kwargs = mock_interaction.followup.send.call_args
    view = kwargs.get("view") or (args[1] if len(args) > 1 else None)
    await JoinView.join_button(view, mock_interaction, view.join_button)

    # 3. 開始 (JoinView)
    await JoinView.start_button(view, mock_interaction, view.start_button)

    # セッション取得
    session = game_manager.get_session(mock_interaction.channel_id)
    assert session is not None
    assert session.status == "playing"

    # 4. PokerView でのアクション
    pk_view = PokerView(session, lambda: game_manager.end_session(mock_interaction.channel_id))

    # 決着するか制限回数までアクション
    max_turns = 30
    while game_manager.get_session(mock_interaction.channel_id) and max_turns > 0:
        current_p = session.get_current_player()
        if not current_p:
            break

        if current_p["id"] == user_id:
            # 自分の番なら Call (Button属性は 'call')
            await PokerView.call(pk_view, mock_interaction, pk_view.call)
        else:
            # NPCの番なら思考をキック
            await session.process_npc_turns(view_callback=AsyncMock())

        max_turns -= 1

    # 決着確認
    assert game_manager.get_session(mock_interaction.channel_id) is None
    # 履歴に精算があるか
    history = wallet.get_history(user_id)
    # ポーカー終了により変動があるか
    if not any("ポーカー" in h["reason"] for h in history):
        pytest.fail(f"History reason 'ポーカー' not found in: {[h['reason'] for h in history]}")
    assert len(history) >= 1
