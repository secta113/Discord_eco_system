from unittest.mock import MagicMock, patch

import pytest

from core.utils.constants import GameType, JPRarity
from logic.blackjack.bj_deck import Deck
from logic.blackjack.bj_models import BlackjackHand, BlackjackPlayer
from logic.blackjack.bj_service import BlackjackService


@patch("logic.blackjack.bj_service.wallet")
@patch("logic.blackjack.bj_service.BetService")
class TestBlackjackService:
    def test_double_down_escrow(self, mock_bet_service, mock_wallet):
        mock_bet_service.escrow.return_value = True
        mock_bet_service.validate_bet.return_value = True
        service = BlackjackService(channel_id=1, bet_amount=100)

        # Setup: Hand with 2 cards
        service.players = [{"id": 123, "name": "Test"}]
        service.player_states[123] = BlackjackPlayer.from_dict(
            123,
            {
                "hands": [
                    {
                        "hand": [("S", "5"), ("H", "6")],
                        "status": "playing",
                        "bet": 100,
                        "is_doubled": False,
                        "hospitality_triggered": False,
                    }
                ],
                "active_hand_index": 0,
            },
        )

        msg, is_done = service.current_player_action(123, "double")
        assert service.player_states[123].hands[0].bet == 200
        mock_bet_service.escrow.assert_called_with(123, 100)
        assert is_done is True

    def test_settle_777(self, mock_bet_service, mock_wallet):
        # 7-7-7 (Triple Seven)
        service = BlackjackService(channel_id=1, bet_amount=100)
        service.players = [{"id": 123, "name": "Test"}]
        service.dealer_hand = [("H", "K"), ("D", "Q")]  # 20
        service.player_states[123] = BlackjackPlayer.from_dict(
            123,
            {
                "hands": [
                    {
                        "hand": [("C", "7"), ("D", "7"), ("S", "7")],
                        "status": "stand",
                        "bet": 100,
                        "is_doubled": False,
                        "hospitality_triggered": False,
                    }
                ],
                "active_hand_index": 0,
            },
        )

        mock_bet_service.execute_jackpot.return_value = 300  # Mock 30% (assuming pool 1000)
        mock_bet_service.payout.return_value = 2100  # Mock 21x

        results = service.settle_all()

        assert "7-7-7" in results[0]["hands"][0]["result"]
        # payout should be called with 21x bet
        mock_bet_service.payout.assert_called()
        mock_bet_service.execute_jackpot.assert_called_with(
            123, GameType.BLACKJACK, JPRarity.EPIC, "🎰 **7-7-7!**"
        )

    def test_settle_suited_bj(self, mock_bet_service, mock_wallet):
        # Suited Blackjack
        service = BlackjackService(channel_id=1, bet_amount=100)
        service.players = [{"id": 123, "name": "Test"}]
        service.dealer_hand = [("H", "K"), ("D", "Q")]  # 20
        service.player_states[123] = BlackjackPlayer.from_dict(
            123,
            {
                "hands": [
                    {
                        "hand": [("S", "A"), ("S", "K")],
                        "status": "blackjack",
                        "bet": 100,
                        "is_doubled": False,
                        "hospitality_triggered": False,
                    }
                ],
                "active_hand_index": 0,
            },
        )

        from logic.bet_service import BetService

        mock_wallet.load_balance.side_effect = lambda uid: (
            5000 if uid == BetService.SYSTEM_JACKPOT_ID else 10000
        )
        mock_bet_service.payout.return_value = 250  # 2.5x

        results = service.settle_all()
        assert "Suited Blackjack" in results[0]["hands"][0]["result"]
        # Should also call payout for the 1000 pts bonus
        assert mock_bet_service.payout.call_count >= 2

    @patch("logic.blackjack.bj_hospitality.random.random")
    @patch("logic.blackjack.bj_hospitality.GameLogicService.get_hospitality_rate")
    def test_hospitality_bust_avoidance(
        self, mock_h_rate, mock_random, mock_bet_service, mock_wallet
    ):
        # Trigger Hospitality
        mock_h_rate.return_value = 1.0  # 100% chance
        mock_random.return_value = 0.0  # Trigger

        service = BlackjackService(channel_id=1, bet_amount=100)
        service.players = [{"id": 123, "name": "Test"}]
        service.player_states[123] = BlackjackPlayer.from_dict(
            123,
            {
                "hands": [
                    {
                        "hand": [("S", "K"), ("H", "5")],  # 15
                        "status": "playing",
                        "bet": 100,
                        "is_doubled": False,
                        "hospitality_triggered": False,
                    }
                ],
                "active_hand_index": 0,
            },
        )
        # Card at top of deck is a 10 (would bust)
        service.deck.cards = [("D", "K"), ("S", "2")]

        # Mock peek/draw/move
        service.deck.peek = MagicMock(return_value=("D", "K"))
        service.deck.move_top_to_bottom = MagicMock()

        msg, is_done = service.current_player_action(123, "hit")
        # move_top_to_bottom should be called because of hospitality
        service.deck.move_top_to_bottom.assert_called()
        assert service.player_states[123].hands[0].hospitality_triggered is True

    @patch("logic.blackjack.bj_hospitality.random.random")
    @patch("logic.blackjack.bj_hospitality.GameLogicService.get_hospitality_rate")
    @patch("logic.blackjack.bj_hospitality.Deck.swap_top_with_ten")
    def test_blackjack_dealer_hospitality_v2_4(
        self, mock_swap, mock_h_rate, mock_random, mock_bet_service, mock_wallet
    ):
        """BJディーラー接待が全プレイヤーの最高レートで発動することを確認"""
        mock_random.return_value = 0.0  # 常に発動
        mock_swap.return_value = True

        mock_h_rate.side_effect = lambda uid: 0.40 if uid == 123 else 0.05

        service = BlackjackService(1, 100)
        service.players = [{"id": 123, "name": "PoorPlayer"}]
        service.player_states[123] = BlackjackPlayer.from_dict(
            123,
            {
                "hands": [
                    {
                        "hand": [("S", "2"), ("H", "3")],
                        "status": "playing",
                        "bet": 100,
                        "is_doubled": False,
                        "hospitality_triggered": False,
                    }
                ],
                "active_hand_index": 0,
            },
        )
        service.dealer_hand = [("H", "6"), ("S", "8")]  # 14

        with patch("logic.blackjack.bj_hospitality.Deck.peek") as mock_peek:
            mock_peek.return_value = ("D", "7")
            service.dealer_turn()
            assert mock_swap.called
            assert service.player_states[123].hands[0].hospitality_triggered is True

    @patch("logic.blackjack.bj_hospitality.random.random")
    @patch("logic.blackjack.bj_hospitality.GameLogicService.get_hospitality_rate")
    @patch("logic.blackjack.bj_hospitality.Deck.swap_top_with_ten")
    def test_blackjack_dealer_hospitality_protects_rare_hand(
        self, mock_swap, mock_h_rate, mock_random, mock_bet_service, mock_wallet
    ):
        """レア役が確定しているプレイヤーには接待フラグ（ペナルティ）が付与されないことを確認"""
        mock_random.return_value = 0.0
        mock_swap.return_value = True
        mock_h_rate.return_value = 0.40
        service = BlackjackService(1, 100)
        service.players = [{"id": 123, "name": "Winner"}]
        service.player_states[123] = BlackjackPlayer.from_dict(
            123,
            {
                "hands": [
                    {
                        "hand": [("S", "7"), ("H", "7"), ("D", "7")],
                        "status": "stand",
                        "bet": 100,
                        "is_doubled": False,
                        "hospitality_triggered": False,
                    }
                ],
                "active_hand_index": 0,
            },
        )
        service.dealer_hand = [("H", "6"), ("S", "8")]
        with patch("logic.blackjack.bj_hospitality.Deck.peek") as mock_peek:
            mock_peek.return_value = ("D", "7")
            service.dealer_turn()
            assert mock_swap.called
            assert service.player_states[123].hands[0].hospitality_triggered is False
