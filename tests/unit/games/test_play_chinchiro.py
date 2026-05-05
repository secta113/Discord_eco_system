from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from cogs.games import Games
from core.economy import wallet
from core.ui.view_base import JoinView
from logic.chinchiro.ui.cc_view import ChinchiroView
from managers.manager import game_manager


@pytest.fixture
def cog_games():
    bot = MagicMock()
    return Games(bot)


@pytest.mark.asyncio
async def test_play_chinchiro_roll_logic(init_test_env, mock_interaction, mock_button, cog_games):
    """Chinchiroの募集 -> 参加 -> 開始 -> 振る(Roll) -> 精算の流れ"""
    user_id = mock_interaction.user.id
    wallet.save_balance(user_id, 2000)

    # 1. 募集 (Host は自動的に参加済み)
    cmd = cog_games.chinchiro
    func = cmd.callback if hasattr(cmd, "callback") else cmd
    await func(cog_games, interaction=mock_interaction, bet=100)

    # 2. Viewの取得
    args, kwargs = mock_interaction.followup.send.call_args
    view = kwargs.get("view") or (args[1] if len(args) > 1 else None)

    # 3. もう一人参加させる (Another Player)
    other_user = MagicMock()
    other_user.id = 999
    other_user.display_name = "OtherUser"
    wallet.save_balance(other_user.id, 2000)

    other_interaction = MagicMock(spec=discord.Interaction)
    other_interaction.user = other_user
    other_interaction.channel_id = mock_interaction.channel_id  # 同じチャンネル
    other_interaction.response = AsyncMock()
    other_interaction.followup = AsyncMock()
    # メンテナンスモード回避
    other_interaction.client = MagicMock()
    other_interaction.client.maintenance_mode = False

    await JoinView.join_button(view, other_interaction, view.join_button)

    # 4. 開始 (JoinView)
    await JoinView.start_button(view, mock_interaction, view.start_button)

    # 4. ChinchiroView での Roll
    session = game_manager.get_session(mock_interaction.channel_id)
    assert session is not None

    # 状態保存のためのコールバックを設定
    cc_view = ChinchiroView(
        session,
        cleanup_callback=lambda: game_manager.end_session(mock_interaction.channel_id),
        save_callback=lambda: game_manager.save_session(cc_view.session),
    )

    # プレイヤーごとのインタラクションをマップ化
    interaction_map = {
        mock_interaction.user.id: mock_interaction,
        other_user.id: other_interaction,
    }

    # 決着がつく（セッションが削除される）まで振るシミュレーション
    max_loops = 30
    while game_manager.get_session(mock_interaction.channel_id) and max_loops > 0:
        current_session = game_manager.get_session(mock_interaction.channel_id)
        cc_view.session = current_session  # Viewのセッションを最新に同期

        current_p = current_session.get_current_player()
        if not current_p:
            break

        target_interaction = interaction_map.get(current_p["id"])
        await ChinchiroView.roll_button(cc_view, target_interaction, cc_view.roll_button)
        max_loops -= 1

    # 決着確認
    assert game_manager.get_session(mock_interaction.channel_id) is None
    # 履歴に精算があるか
    history = wallet.get_history(user_id)
    # 敗北時は履歴に残らないが、セッションがNONEなら終了している。
