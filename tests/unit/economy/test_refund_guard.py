from unittest.mock import MagicMock, patch

import pytest

from managers.game_session import BaseGameSession


def test_refund_all_skips_npc():
    # Setup
    session = BaseGameSession(123, 100)
    # Human (ID > 0) and NPC (ID < 0)
    session.players = [{"id": 1, "name": "Human"}, {"id": -1, "name": "Bot1"}]

    with patch("managers.game_session.BetService.payout") as mock_payout:
        # Execute
        session.refund_all()

        # Verify
        # 1. Payout called for human
        mock_payout.assert_any_call(1, 100)
        # 2. Payout NOT called for NPC
        # Check all calls to see if -1 was ever used
        for call in mock_payout.call_args_list:
            assert call[0][0] != -1

        # 3. Exactly one payout call
        assert mock_payout.call_count == 1
        # 4. Status is cancelled
        assert session.status == "cancelled"
