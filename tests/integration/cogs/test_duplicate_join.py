from unittest.mock import MagicMock, patch

import pytest

from logic.poker.pk_service import TexasPokerService
from managers.game_session import BaseGameSession


def test_duplicate_join_prevention_base():
    session = BaseGameSession(123, 100)
    user = MagicMock()
    user.id = 1
    user.display_name = "User1"

    with patch("managers.game_session.BetService.escrow", return_value=True):
        # 1st join
        assert session.add_player(user) is True
        assert len(session.players) == 1

        # 2nd join with same ID should raise GameActionError
        from managers.manager import GameActionError

        with pytest.raises(GameActionError):
            session.add_player(user)
        assert len(session.players) == 1


def test_duplicate_join_prevention_poker():
    session = TexasPokerService(123, 100)
    user = MagicMock()
    user.id = 1
    user.display_name = "User1"

    with patch("logic.poker.pk_service.wallet.load_balance", return_value=10000):
        with patch("logic.poker.pk_service.BetService.escrow", return_value=True):
            # 1st join
            assert session.add_player(user) is True
            assert len(session.players) == 1

            # 2nd join with same ID should raise GameActionError
            from managers.manager import GameActionError

            with pytest.raises(GameActionError):
                session.add_player(user)
            assert len(session.players) == 1
