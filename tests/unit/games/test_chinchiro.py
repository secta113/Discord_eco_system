from unittest.mock import MagicMock, patch

import pytest

from logic.chinchiro.cc_models import ChinchiroHand, ChinchiroPlayer
from logic.chinchiro.cc_rules import ChinchiroRules
from logic.chinchiro.cc_service import ChinchiroService


class TestChinchiroService:
    def test_hand_calculation(self):
        # Rules 側で判定
        # Pinzoro
        assert ChinchiroRules.calculate_role([1, 1, 1])[0] == "ピンゾロ"

        # Arashi
        name, strength = ChinchiroRules.calculate_role([6, 6, 6])
        assert name == "6のアラシ"
        assert strength == 2006

        # Shigoro
        assert ChinchiroRules.calculate_role([4, 5, 6])[0] == "シゴロ"

        # Hifumi
        assert ChinchiroRules.calculate_role([1, 2, 3])[0] == "ヒフミ"

        # Regular
        assert ChinchiroRules.calculate_role([1, 1, 3])[0] == "3の目"

        # No Role
        assert ChinchiroRules.calculate_role([1, 4, 3])[0] == "目なし"

    @patch("logic.chinchiro.cc_service.BetService.payout")
    def test_finalize_settlement(self, mock_payout):
        service = ChinchiroService(1, 100)
        service.players = [{"id": 1, "name": "Winner"}, {"id": 2, "name": "Loser"}]
        service.pot = 200

        # Winner Hand
        h1 = ChinchiroHand([4, 5, 6], 1)
        h1.role_name = "シゴロ"
        h1.strength = 1000
        p1 = ChinchiroPlayer(1)
        p1.set_hand(h1)

        # Loser Hand
        h2 = ChinchiroHand([1, 2, 4], 3)
        h2.role_name = "目なし"
        h2.strength = 0
        p2 = ChinchiroPlayer(2)
        p2.set_hand(h2)

        service.player_states = {1: p1, 2: p2}

        mock_payout.return_value = 210  # 200 + 5% bonus

        # Net Pot = 200 - (200 * 0.05) = 190 (because ID 1 is Oya)
        winner, sorted_scores, payout = service.finalize()
        assert winner["id"] == 1
        assert payout == 210
        mock_payout.assert_any_call(1, 190, is_pvp=True, reason="チンチロリン勝利配当")

    @patch("logic.chinchiro.cc_service.BetService.payout")
    @patch("logic.chinchiro.cc_service.BetService.add_to_jackpot_real_only")
    def test_oya_tax(self, mock_jp, mock_payout):
        # Winner is the Dealer (1st player)
        service = ChinchiroService(1, 100)
        service.players = [{"id": 1, "name": "Dealer"}, {"id": 2, "name": "Player"}]
        service.pot = 200

        service.player_states = {1: ChinchiroPlayer(1), 2: ChinchiroPlayer(2)}
        service.player_states[1].set_hand(ChinchiroHand([6, 6, 2], 1))
        service.player_states[2].set_hand(ChinchiroHand([1, 1, 2], 1))

        # Force dealer win
        service.player_states[1].hand.strength = 106
        service.player_states[2].hand.strength = 102

        mock_payout.return_value = 199  # (190 * 1.05)

        service.finalize()

        # Net Pot = 200 - (200 * 0.05) = 190
        # Payout should be called ONCE with net amount and is_pvp=True
        mock_payout.assert_called_once_with(1, 190, is_pvp=True, reason="チンチロリン勝利配当")
        # Tax (10) should be added to Jackpot via real_only check
        mock_jp.assert_called_with(10, 200, 200, "Chinchiro")

    @patch("logic.chinchiro.cc_hospitality.random.random")
    @patch("logic.chinchiro.cc_hospitality.GameLogicService.get_hospitality_rate")
    def test_hospitality_no_role_avoidance(self, mock_h_rate, mock_random):
        mock_h_rate.return_value = 1.0  # 100%
        mock_random.return_value = 0.0  # Trigger

        service = ChinchiroService(1, 100)
        service.players = [{"id": 1, "name": "Test"}]
        service.current_roll_count = 2

        with patch("logic.chinchiro.cc_hospitality.random.randint") as mock_randint:
            # First roll (in service): [1, 2, 4] (no role) -> 3 ints
            # Hospitality rerolls: [1, 2, 4] again -> 3 ints
            # Forcing [x, x, p] -> 1 int for p
            mock_randint.side_effect = [
                1,
                2,
                4,  # Initial roll in roll_action
                1,
                2,
                4,  # Reroll in cc_hospitality
                3,  # Forced point in cc_hospitality
            ]

            dice, dice_str, role_name, strength, is_fixed, h_triggered = service.roll_action(1)

            assert h_triggered is True
            assert "の目" in role_name
            assert strength > 100

    @patch("logic.chinchiro.cc_hospitality.random.random")
    @patch("logic.chinchiro.cc_hospitality.BetService.get_user_status")
    def test_chinchiro_hospitality_timing(self, mock_status, mock_random):
        """チンチロの接待が3投目のみ発動することを確認"""
        mock_status.return_value = "Recovery"
        mock_random.return_value = 0.0  # 常に発動条件を満たす

        service = ChinchiroService(1, 100)
        service.players = [{"id": 123, "name": "Test"}]

        # 1投目: 目なしを仕込む
        with patch("logic.chinchiro.cc_service.random_randint") as mock_randint:
            mock_randint.side_effect = [1, 2, 4]  # 目なし
            dice, dice_str, role_name, strength, is_fixed, h_triggered = service.roll_action(123)
            assert h_triggered is False  # 1投目なので発動しないはず
            assert role_name == "目なし"
            assert service.current_roll_count == 1

        # 2投目: 目なしを仕込む
        with patch("logic.chinchiro.cc_service.random_randint") as mock_randint:
            mock_randint.side_effect = [1, 2, 4]
            dice, dice_str, role_name, strength, is_fixed, h_triggered = service.roll_action(123)
            assert h_triggered is False  # 2投目なので発動しないはず
            assert service.current_roll_count == 2

        # 3投目: 目なしを仕込む -> ここで発動するはず
        # cc_service.random_randint (初回) + cc_hospitality.random.randint (リロール)
        with patch("logic.chinchiro.cc_service.random_randint") as mock_service_randint:
            with patch("logic.chinchiro.cc_hospitality.random.randint") as mock_hosp_randint:
                mock_service_randint.side_effect = [1, 2, 4]  # 元の目なし
                mock_hosp_randint.side_effect = [
                    1,
                    2,
                    4,  # 接待リロールの目なし
                    3,  # 強制「○の目」の1投目
                ]
                dice, dice_str, role_name, strength, is_fixed, h_triggered = service.roll_action(
                    123
                )
                assert h_triggered is True  # 3投目なので発動
                assert "の目" in role_name
                assert service.current_roll_count == 3
