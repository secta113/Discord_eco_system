from unittest.mock import patch

from logic.economy.bonus import BonusService
from logic.economy.game_logic import GameLogicService
from logic.economy.status import StatusService


class TestEconomyV24:
    @patch("core.economy.wallet.get_all_balances")
    def test_benchmark_adaptive(self, mock_get_all):
        # Case 1: N <= 10 (Mean)
        mock_get_all.return_value = {1: 1000, 2: 2000, 3: 3000}  # Mean: 2000
        assert StatusService.get_benchmark() == 2000.0

        # Case 2: N > 10 (Median)
        balances = {i: i * 100 for i in range(1, 13)}  # 100, 200, ..., 1200. N=12. Median: 650
        mock_get_all.return_value = balances
        assert StatusService.get_benchmark() == 650.0

    @patch("core.economy.wallet.get_all_balances")
    @patch("core.economy.wallet.load_balance")
    def test_user_status(self, mock_load, mock_get_all):
        mock_get_all.return_value = {1: 10000, 2: 10000, 3: 10000}  # Benchmark: 10000

        # Prime: > 10000
        mock_load.return_value = 15000
        assert StatusService.get_user_status(100) == "Prime"

        # Standard: 3000 <= x <= 10000
        mock_load.return_value = 5000
        assert StatusService.get_user_status(101) == "Standard"

        # Recovery: < 3000
        mock_load.return_value = 1000
        assert StatusService.get_user_status(102) == "Recovery"

    @patch("logic.economy.bonus.JackpotService.claim_overflow_dividend")
    @patch("core.economy.wallet.load_balance")
    @patch("core.economy.wallet.get_last_daily")
    @patch("core.economy.wallet.save_balance")
    @patch("core.economy.wallet.set_last_daily")
    @patch("core.economy.wallet.add_history")
    @patch("logic.economy.status.StatusService.get_benchmark")
    @patch("logic.economy.status.StatusService.get_user_status")
    def test_daily_bonus_calc(
        self,
        mock_status,
        mock_bench,
        mock_add_hist,
        mock_set_daily,
        mock_save,
        mock_last,
        mock_load,
        mock_jod,
    ):
        mock_jod.return_value = 0
        mock_last.return_value = None
        mock_bench.return_value = 10000.0

        # Case: Prime (Balance: 20000)
        # Total: 1000 + MAX(200, 500) = 1500
        mock_load.return_value = 20000
        mock_status.return_value = "Prime"
        success, _ = BonusService.claim_daily(1)
        assert success is True
        mock_save.assert_called_with(1, 21500)

        # Case: Standard (Balance: 5000)
        # Total: 1000 + 500 = 1500
        mock_load.return_value = 5000
        mock_status.return_value = "Standard"
        success, _ = BonusService.claim_daily(2)
        assert success is True
        mock_save.assert_called_with(2, 6500)

        # Case: Recovery (Balance: 1000)
        # Total: 1000 + 500 + (3000 - 1000)*0.5 = 2500
        mock_load.return_value = 1000
        mock_status.return_value = "Recovery"
        success, _ = BonusService.claim_daily(3)
        assert success is True
        mock_save.assert_called_with(3, 3500)

    @patch("logic.bet_service.BetService.get_user_status")
    def test_hospitality_rates(self, mock_status):
        mock_status.return_value = "Prime"
        assert GameLogicService.get_hospitality_rate(1) == 0.05

        mock_status.return_value = "Standard"
        assert GameLogicService.get_hospitality_rate(2) == 0.20

        mock_status.return_value = "Recovery"
        assert GameLogicService.get_hospitality_rate(3) == 0.40

    @patch("logic.economy.bonus.JackpotService.claim_overflow_dividend")
    @patch("logic.economy.bonus.wallet.save_balance")
    @patch("logic.economy.bonus.wallet.get_last_daily")
    @patch("logic.economy.bonus.wallet.set_last_daily")
    @patch("logic.economy.bonus.StatusService.get_user_status")
    @patch("logic.economy.bonus.StatusService.get_benchmark")
    @patch("logic.economy.bonus.wallet.load_balance")
    @patch("logic.economy.bonus.wallet.add_history")
    def test_system_daily_bonus_auto_trigger(
        self,
        mock_history,
        mock_load,
        mock_benchmark,
        mock_status,
        mock_set_last,
        mock_get_last,
        mock_save,
        mock_jod,
    ):
        """システム（ID 0）のデイリーボーナスが自動でトリガーされることを確認"""
        mock_jod.return_value = 0
        mock_benchmark.return_value = 10000
        mock_get_last.side_effect = lambda uid: "2000-01-01"
        mock_load.return_value = 5000
        mock_status.side_effect = lambda uid: "System" if uid == 0 else "Standard"
        BonusService.claim_daily(123)
        assert mock_save.call_count == 2  # System + User
