from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from managers.starter import execute_game_start


@pytest.mark.asyncio
async def test_poker_npc_first_turn_triggers_auto_turns():
    # Setup
    channel_id = 123
    interaction = AsyncMock()
    interaction.channel_id = channel_id
    interaction.response.is_done.return_value = False

    # Mock Session
    session = MagicMock()
    session.game_type = "poker"
    session.players = [{"id": -1, "name": "Bot1", "mention": "Bot1"}]
    session.get_current_player.return_value = session.players[0]
    session.phase = "pre_flop"
    session.status = "recruiting"

    # Mock View
    with (
        patch("managers.starter.PokerView") as mock_view_cls,
        patch("managers.starter.game_manager.save_session"),
    ):
        mock_view = MagicMock()
        mock_view.session = session
        mock_view._npc_action_callback = AsyncMock()
        mock_view_cls.return_value = mock_view

        # Mock process_npc_turns and update_display
        session.process_npc_turns = AsyncMock(return_value=True)
        mock_view.update_display = AsyncMock()

        # Execute
        await execute_game_start(interaction, session)

        # Verify
        # 1. update_display was called for initial status
        mock_view.update_display.assert_any_call(
            interaction, "テキサス・ホールデム 開始！\n最初のターン: Bot1", is_first=True
        )

        # 2. process_npc_turns was called because first player is NPC
        session.process_npc_turns.assert_called_once_with(
            view_callback=mock_view._npc_action_callback
        )
