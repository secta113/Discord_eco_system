from unittest.mock import patch

import pytest

from logic.bet_service import BetService
from logic.constants import GameType, JPRarity


class TestBetService:
    @patch("logic.bet_service.StatusService.get_user_status")
    @patch("logic.bet_service.EconomyProvider.payout")
    def test_payout_with_pvp_bonus(self, mock_payout, mock_status):
        # Case 1: Prime User (1.05x bonus)
        mock_status.return_value = "Prime"
        BetService.payout(123, 1000, is_pvp=True, reason="Test")
        # bonus_rate should be 0.05
        mock_payout.assert_called_with(123, 1000, bonus_rate=0.05, reason="Test")

        # Case 2: Standard User (1.5x multiplier on bonus_rate)
        # 0.05 * 1.5 = 0.075
        mock_status.return_value = "Standard"
        BetService.payout(456, 1000, is_pvp=True, reason="Test")
        # Use call_args to check with approx for floating point precision
        args, kwargs = mock_payout.call_args
        assert args == (456, 1000)
        assert kwargs["bonus_rate"] == pytest.approx(0.075)
        assert kwargs["reason"] == "Test"

    @patch("logic.bet_service.JackpotService.add_to_jackpot")
    def test_add_to_jackpot(self, mock_add):
        BetService.add_to_jackpot(500)
        mock_add.assert_called_with(500)

    @patch("logic.bet_service.StatusService.get_user_status")
    @patch("logic.bet_service.EconomyProvider.payout")
    def test_bet_service_payout_rubberband_v2_4(self, mock_payout, mock_status):
        """BetService.payout が Standard/Recovery にボーナスを適用することを確認"""
        mock_status.return_value = "Standard"
        BetService.payout(123, 1000, is_pvp=True)
        args, kwargs = mock_payout.call_args
        assert pytest.approx(kwargs["bonus_rate"]) == 0.075

        mock_status.return_value = "Recovery"
        BetService.payout(456, 1000, is_pvp=True)
        args, kwargs = mock_payout.call_args
        assert pytest.approx(kwargs["bonus_rate"]) == 0.075

        mock_status.return_value = "Prime"
        BetService.payout(789, 1000, is_pvp=True)
        args, kwargs = mock_payout.call_args
        assert pytest.approx(kwargs["bonus_rate"]) == 0.05
