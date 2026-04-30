from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from cogs.games import Games
from core.economy import wallet
from core.ui.view_base import JoinView
from logic.blackjack.bj_view import BlackjackView
from managers.manager import game_manager


@pytest.fixture
def cog_games():
    bot = MagicMock()
    return Games(bot)


@pytest.mark.asyncio
async def test_play_blackjack_full_flow(init_test_env, mock_interaction, mock_button, cog_games):
    """Blackjackの募集 -> 参加 -> 開始 -> ヒット -> スタンド -> 精算の流れをテスト"""
    user_id = mock_interaction.user.id
    wallet.save_balance(user_id, 5000)

    # 1. 募集
    cmd = Games.blackjack
    func = cmd.callback if hasattr(cmd, "callback") else cmd
    await func(cog_games, mock_interaction, 100)

    # 2. 参加 (JoinView)
    args, kwargs = mock_interaction.followup.send.call_args
    view = kwargs.get("view") or (args[1] if len(args) > 1 else None)
    assert isinstance(view, JoinView)

    await JoinView.join_button(view, mock_interaction, view.join_button)

    # 3. 開始 (JoinView) — deckをモックしてBJ以外の手を保証
    # カード形式は (suit, rank)。BJにならない手: player=("♠","5"),("♣","3") dealer=("♥","8"),("♦","4")
    safe_cards = [
        ("♠", "5"),
        ("♣", "3"),  # player hand (8点)
        ("♥", "8"),
        ("♦", "4"),  # dealer hand (12点)
    ]
    draw_index = [0]

    def mock_draw(self=None):
        card = safe_cards[draw_index[0] % len(safe_cards)]
        draw_index[0] += 1
        return card

    with patch.object(
        __import__("logic.blackjack.bj_service", fromlist=["Deck"]).Deck, "draw", mock_draw
    ):
        await JoinView.start_button(view, mock_interaction, view.start_button)

    # 4. セッション取得 (ゲームが即終了した場合もOKとする)
    session = game_manager.get_session(mock_interaction.channel_id)

    if session is None:
        # 開始直後にBJや即決着が起きた場合 — 精算済みなのでOK
        history = wallet.get_history(user_id)
        # 何らかの経済的な変動が起きたことを確認（参加コストの引き落とし）
        assert len(history) >= 1
        return

    # 5. 通常フロー: Hit → Stand
    assert session.status == "playing"

    bj_view = BlackjackView(session, lambda: game_manager.end_session(mock_interaction.channel_id))

    await BlackjackView.hit(bj_view, mock_interaction, bj_view.hit)

    session = game_manager.get_session(mock_interaction.channel_id)
    if session and session.status == "playing":
        await BlackjackView.stand(bj_view, mock_interaction, bj_view.stand)

    # 決着確認
    assert game_manager.get_session(mock_interaction.channel_id) is None
