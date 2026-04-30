import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from logic.bet_service import BetService


def test_add_to_jackpot_real_only():
    print("Testing BetService.add_to_jackpot_real_only...")

    with patch("logic.bet_service.JackpotService.add_to_jackpot") as mock_add:
        # Case 1: 100% human (300/300)
        res = BetService.add_to_jackpot_real_only(15, 300, 300)
        print(f"Case 1 (100% real): Expected 15, Got {res}")
        assert res == 15
        mock_add.assert_called_with(15)
        mock_add.reset_mock()

        # Case 2: 1/3 human (100/300)
        res = BetService.add_to_jackpot_real_only(15, 300, 100)
        print(f"Case 2 (1/3 real): Expected 5, Got {res}")
        assert res == 5
        mock_add.assert_called_with(5)
        mock_add.reset_mock()

        # Case 3: 0% human (0/300)
        res = BetService.add_to_jackpot_real_only(15, 300, 0)
        print(f"Case 3 (0% real): Expected 0, Got {res}")
        assert res == 0
        mock_add.assert_not_called()
        mock_add.reset_mock()

        # Case 4: Human bet exceeds total (should not happen, but capped at 1.0)
        res = BetService.add_to_jackpot_real_only(10, 100, 200)
        print(f"Case 4 (Exceed cap): Expected 10, Got {res}")
        assert res == 10
        mock_add.assert_called_with(10)
        mock_add.reset_mock()

    print("All test cases passed!")


if __name__ == "__main__":
    try:
        test_add_to_jackpot_real_only()
    except AssertionError as e:
        print("❌ Test failed!")
        sys.exit(1)
