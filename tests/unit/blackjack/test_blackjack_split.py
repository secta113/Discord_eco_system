from unittest.mock import MagicMock, patch

import pytest

from logic.blackjack.bj_deck import Deck
from logic.blackjack.bj_models import BlackjackHand, BlackjackPlayer
from logic.blackjack.bj_service import BlackjackService


@patch("logic.blackjack.bj_service.wallet")
@patch("logic.blackjack.bj_service.BetService")
class TestBlackjackSplit:
    def test_split_action_success(self, mock_bet_service, mock_wallet):
        mock_bet_service.escrow.return_value = True
        mock_bet_service.validate_bet.return_value = True
        service = BlackjackService(channel_id=1, bet_amount=100)

        # Setup: Hand with two 10s
        uid = 123
        service.players = [{"id": uid, "name": "Test", "mention": "@Test"}]
        service.player_states[uid] = BlackjackPlayer.from_dict(
            uid,
            {
                "hands": [
                    {
                        "hand": [("S", "10"), ("H", "10")],
                        "status": "playing",
                        "bet": 100,
                        "is_doubled": False,
                        "hospitality_triggered": False,
                    }
                ],
                "active_hand_index": 0,
            },
        )
        # Mock deck to return specific cards for the new draws
        service.deck.draw = MagicMock()
        service.deck.draw.side_effect = [("D", "5"), ("C", "2")]

        msg, is_turn_end = service.current_player_action(uid, "split")
        assert service.player_states[uid].hands[0].bet == 100
        assert service.player_states[uid].hands[1].bet == 100
        assert mock_bet_service.escrow.called is True
        # Hand 1: S10 + D5 (15)
        assert service.player_states[uid].hands[0].cards == [("S", "10"), ("D", "5")]
        # Hand 2: H10 + C2 (12)
        assert service.player_states[uid].hands[1].cards == [("H", "10"), ("C", "2")]
        # Turn should NOT end yet because Hand 1 is "playing"
        assert is_turn_end is False

    def test_split_turn_progression(self, mock_bet_service, mock_wallet):
        mock_bet_service.escrow.return_value = True
        service = BlackjackService(channel_id=1, bet_amount=100)

        uid = 123
        service.players = [{"id": uid, "name": "Test", "mention": "@Test"}]
        # Already split
        service.player_states[uid] = BlackjackPlayer.from_dict(
            uid,
            {
                "hands": [
                    {
                        "hand": [("S", "10"), ("D", "5")],
                        "status": "playing",
                        "bet": 100,
                        "is_doubled": False,
                        "hospitality_triggered": False,
                    },
                    {
                        "hand": [("H", "10"), ("C", "2")],
                        "status": "playing",
                        "bet": 100,
                        "is_doubled": False,
                        "hospitality_triggered": False,
                    },
                ],
                "active_hand_index": 0,
            },
        )

        # Action 1: Stand on Hand 1
        msg, is_turn_end = service.current_player_action(uid, "stand")
        assert service.player_states[uid].hands[0].status == "stand"
        # Turn should NOT end because Hand 2 is still "playing"
        assert (
            is_turn_end is True
        )  # current_player_action returns True for is_turn_end when hand is finished

        # Advance turn if needed (handled by View in actual game)
        has_next = service.advance_turn_if_needed()
        assert has_next is True
        assert service.player_states[uid].active_hand_index == 1

        # Action 2: Hit on Hand 2
        service.deck.draw = MagicMock(return_value=("S", "9"))  # 10+2+9 = 21
        msg, is_turn_end = service.current_player_action(uid, "hit")
        assert (
            service.player_states[uid].hands[1].status == "playing"
        )  # still playing (could hit more unless 21 forces stand)

        # Action 3: Stand on Hand 2
        msg, is_turn_end = service.current_player_action(uid, "stand")
        assert is_turn_end is True
        has_next = service.advance_turn_if_needed()
        assert has_next is False  # End of players

    def test_split_settlement(self, mock_bet_service, mock_wallet):
        service = BlackjackService(channel_id=1, bet_amount=100)
        uid = 123
        service.players = [{"id": uid, "name": "Test"}]
        service.dealer_hand = [("D", "K"), ("S", "9")]  # 19

        service.player_states[uid] = BlackjackPlayer.from_dict(
            uid,
            {
                "hands": [
                    {
                        "hand": [("S", "10"), ("D", "K")],
                        "status": "stand",
                        "bet": 100,
                        "is_doubled": False,
                        "hospitality_triggered": False,
                    },  # 20 (Win)
                    {
                        "hand": [("H", "10"), ("C", "7")],
                        "status": "stand",
                        "bet": 100,
                        "is_doubled": False,
                        "hospitality_triggered": False,
                    },  # 17 (Lose)
                ],
                "active_hand_index": 1,
            },
        )

        # Mock payout to return values
        mock_bet_service.payout.side_effect = [
            200,
            0,
        ]  # 2x for Win, 0 for Lose

        results = service.settle_all()

        assert len(results) == 1
        assert len(results[0]["hands"]) == 2
        assert "🎉 Win" in results[0]["hands"][0]["result"]
        assert "💀 Lose" in results[0]["hands"][1]["result"]
        # payout should be called for the win
        assert mock_bet_service.payout.called is True

    def test_split_mixed_tens(self, mock_bet_service, mock_wallet):
        mock_bet_service.escrow.return_value = True
        mock_bet_service.validate_bet.return_value = True
        service = BlackjackService(channel_id=1, bet_amount=100)

        uid = 123
        service.players = [{"id": uid, "name": "Test", "mention": "@Test"}]
        # 10 and J (both value 10)
        service.player_states[uid] = BlackjackPlayer.from_dict(
            uid,
            {
                "hands": [
                    {
                        "hand": [("S", "10"), ("H", "J")],
                        "status": "playing",
                        "bet": 100,
                        "is_doubled": False,
                        "hospitality_triggered": False,
                    }
                ],
                "active_hand_index": 0,
            },
        )
        service.deck.draw = MagicMock(side_effect=[("D", "5"), ("C", "2")])

        msg, is_turn_end = service.current_player_action(uid, "split")

        assert len(service.player_states[uid].hands) == 2
        assert service.player_states[uid].hands[0].cards[0] == ("S", "10")
        assert service.player_states[uid].hands[1].cards[0] == ("H", "J")
