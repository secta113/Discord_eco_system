import unittest
from unittest.mock import MagicMock, patch

from logic.bet_service import BetService
from logic.economy.status import StatusService


class TestBetLimit(unittest.TestCase):
    def setUp(self):
        # Clear any caches if they exist
        pass

    @patch("core.economy.wallet.load_balance")
    @patch("logic.economy.status.StatusService.get_user_status")
    def test_recovery_limit(self, mock_get_status, mock_load_balance):
        user_id = 123
        mock_get_status.return_value = "Recovery"
        # Balance 20,000 -> 15% = 3,000
        mock_load_balance.return_value = 20000

        # Case 1: <= 10,000 is always allowed
        self.assertTrue(BetService.validate_bet(user_id, 10000))

        # Case 2: > 10,000 and > limit(3,000) -> FAIL (Raises Exception)
        from logic.economy.eco_exceptions import BetLimitViolationError

        with self.assertRaises(BetLimitViolationError) as cm:
            BetService.validate_bet(user_id, 10001)
        self.assertIn("15%", str(cm.exception))
        self.assertIn("3000 pts", str(cm.exception))

    @patch("core.economy.wallet.load_balance")
    @patch("logic.economy.status.StatusService.get_user_status")
    def test_standard_limit(self, mock_get_status, mock_load_balance):
        user_id = 456
        mock_get_status.return_value = "Standard"
        # Balance 100,000 -> 25% = 25,000
        mock_load_balance.return_value = 100000

        # Case 1: 10,000 OK
        self.assertTrue(BetService.validate_bet(user_id, 10000))

        # Case 2: 25,000 OK
        self.assertTrue(BetService.validate_bet(user_id, 25000))

        # Case 3: 25,001 FAIL
        from logic.economy.eco_exceptions import BetLimitViolationError

        with self.assertRaises(BetLimitViolationError) as cm:
            BetService.validate_bet(user_id, 25001)
        self.assertIn("25%", str(cm.exception))
        self.assertIn("25000 pts", str(cm.exception))

    @patch("core.economy.wallet.load_balance")
    @patch("logic.economy.status.StatusService.get_user_status")
    def test_prime_limit(self, mock_get_status, mock_load_balance):
        user_id = 789
        mock_get_status.return_value = "Prime"
        # Balance 1,000,000 -> 50% = 500,000
        mock_load_balance.return_value = 1000000

        # Case 1: 500,000 OK
        self.assertTrue(BetService.validate_bet(user_id, 500000))

        # Case 2: 500,001 FAIL
        from logic.economy.eco_exceptions import BetLimitViolationError

        with self.assertRaises(BetLimitViolationError) as cm:
            BetService.validate_bet(user_id, 500001)
        self.assertIn("50%", str(cm.exception))
        self.assertIn("500000 pts", str(cm.exception))

    @patch("core.economy.wallet.load_balance")
    @patch("logic.economy.status.StatusService.get_user_status")
    def test_low_balance_exemption(self, mock_get_status, mock_load_balance):
        user_id = 999
        mock_get_status.return_value = "Recovery"
        # Balance 5,000 -> 15% = 750
        mock_load_balance.return_value = 5000

        # Even though 5,000 > 750, it is allowed because 5,000 <= 10,000
        self.assertTrue(BetService.validate_bet(user_id, 5000))

        # 10,001 is not allowed because it's > 10,000 and > 750
        from logic.economy.eco_exceptions import BetLimitViolationError

        with self.assertRaises(BetLimitViolationError):
            BetService.validate_bet(user_id, 10001)


if __name__ == "__main__":
    unittest.main()
