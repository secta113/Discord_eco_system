import unittest.mock
from unittest.mock import MagicMock

import pytest

from logic.poker.pk_rules import PokerRules
from logic.poker.pk_service import TexasPokerService


class TestPokerRules:
    def test_high_card(self):
        cards = [("♠", "A"), ("♣", "K"), ("♥", "Q"), ("♦", "J"), ("♠", "9"), ("♣", "8"), ("♥", "7")]
        rank, strength, name = PokerRules.get_best_hand(cards)
        assert rank == PokerRules.HAND_RANK_HIGH_CARD
        assert strength[0] == 14  # A

    def test_one_pair(self):
        cards = [("♠", "A"), ("♣", "A"), ("♥", "Q"), ("♦", "J"), ("♠", "9"), ("♣", "8"), ("♥", "7")]
        rank, strength, name = PokerRules.get_best_hand(cards)
        assert rank == PokerRules.HAND_RANK_ONE_PAIR
        assert strength[0] == 14  # A pair

    def test_two_pair(self):
        cards = [("♠", "A"), ("♣", "A"), ("♥", "K"), ("♦", "K"), ("♠", "9"), ("♣", "8"), ("♥", "7")]
        rank, strength, name = PokerRules.get_best_hand(cards)
        assert rank == PokerRules.HAND_RANK_TWO_PAIR
        assert strength[0] == 14  # A pair
        assert strength[1] == 13  # K pair

    def test_straight(self):
        cards = [("♠", "6"), ("♣", "5"), ("♥", "4"), ("♦", "3"), ("♠", "2"), ("♣", "K"), ("♥", "A")]
        rank, strength, name = PokerRules.get_best_hand(cards)
        assert rank == PokerRules.HAND_RANK_STRAIGHT
        assert strength[0] == 6

    def test_straight_low_ace(self):
        cards = [("♠", "A"), ("♣", "2"), ("♥", "3"), ("♦", "4"), ("♠", "5"), ("♣", "K"), ("♥", "Q")]
        rank, strength, name = PokerRules.get_best_hand(cards)
        assert rank == PokerRules.HAND_RANK_STRAIGHT
        assert strength[0] == 5  # 5-high straight

    def test_full_house(self):
        cards = [("♠", "A"), ("♣", "A"), ("♥", "A"), ("♦", "K"), ("♠", "K"), ("♣", "2"), ("♥", "3")]
        rank, strength, name = PokerRules.get_best_hand(cards)
        assert rank == PokerRules.HAND_RANK_FULL_HOUSE
        assert strength[0] == 14  # A trips
        assert strength[1] == 13  # K pair

    def test_kicker_comparison(self):
        """同じペアでもキッカーで勝敗が決まることを確認"""
        # P1: A Pair with K kicker (avoiding straight)
        cards1 = [
            ("♠", "A"),
            ("♣", "A"),
            ("♥", "K"),
            ("♦", "J"),
            ("♠", "4"),
            ("♣", "3"),
            ("♥", "2"),
        ]
        # P2: A Pair with Q kicker
        cards2 = [
            ("♦", "A"),
            ("♥", "A"),
            ("♠", "Q"),
            ("♣", "J"),
            ("♥", "4"),
            ("♦", "3"),
            ("♠", "2"),
        ]

        rank1, strength1, _ = PokerRules.get_best_hand(cards1)
        rank2, strength2, _ = PokerRules.get_best_hand(cards2)

        assert rank1 == rank2 == PokerRules.HAND_RANK_ONE_PAIR
        assert strength1 > strength2  # K(13) > Q(12)


class TestTexasPokerService:
    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        # サービス全体でのモック適用。各マネージャーも含めて差し替える。
        with (
            unittest.mock.patch("core.economy.wallet.load_balance") as mock_load,
            unittest.mock.patch("core.economy.wallet.update_stats") as mock_update_stats,
            unittest.mock.patch("logic.bet_service.BetService.escrow") as mock_escrow,
            unittest.mock.patch("logic.bet_service.BetService.payout") as mock_payout,
            unittest.mock.patch("logic.bet_service.BetService.execute_jackpot") as mock_jp,
        ):
            self.mock_wallet = MagicMock()
            self.mock_wallet.load_balance = mock_load
            self.mock_wallet.update_stats = mock_update_stats
            self.mock_bet_service = MagicMock()
            self.mock_bet_service.escrow = mock_escrow
            self.mock_bet_service.payout = mock_payout
            self.mock_bet_service.execute_jackpot = mock_jp

            # Defaults
            self.mock_wallet.load_balance.return_value = 10000
            self.mock_bet_service.escrow.return_value = True
            self.mock_bet_service.payout.side_effect = lambda uid, amt, **kwargs: amt
            self.mock_bet_service.execute_jackpot.return_value = 0

            yield

    def test_game_flow_to_flop(self):
        self.mock_wallet.load_balance.return_value = 10000
        self.mock_bet_service.escrow.return_value = True
        service = TexasPokerService(channel_id=1, bet_amount=100, target_player_count=2)

        p1 = MagicMock(id=1, display_name="User1")
        p2 = MagicMock(id=2, display_name="User2")
        service.add_player(p1)
        service.add_player(p2)

        service.start_game(button_index=0)
        assert service.phase == "pre_flop"

        # Identify actual positions after shuffle
        p_idx0_id = service.players[0]["id"]
        p_idx1_id = service.players[1]["id"]

        # 2-player: BTN=index 0 acts first in pre-flop
        assert service.get_current_player()["id"] == p_idx0_id
        service.handle_action(p_idx0_id, "call")
        service.handle_action(p_idx1_id, "check")

        assert service.phase == "flop"
        assert len(service.community_cards) == 3

    def test_3_player_turn_rotation(self):
        """3名での手番順序（プリフロップ〜フロップ）の検証"""
        self.mock_wallet.load_balance.return_value = 10000
        self.mock_bet_service.escrow.return_value = True
        service = TexasPokerService(channel_id=1, bet_amount=100, target_player_count=3)

        p_a = MagicMock(id=1, display_name="PlayerA")
        p_b = MagicMock(id=2, display_name="PlayerB")
        p_c = MagicMock(id=3, display_name="PlayerC")
        service.add_player(p_a)
        service.add_player(p_b)
        service.add_player(p_c)

        # Start with button at index 2
        service.start_game(button_index=2)

        # SB=index 0, BB=index 1, BTN/UTG=index 2
        p_idx0_id = service.players[0]["id"]
        p_idx1_id = service.players[1]["id"]
        p_idx2_id = service.players[2]["id"]

        # Pre-flop UTG is index 2
        assert service.get_current_player()["id"] == p_idx2_id
        service.handle_action(p_idx2_id, "call")
        # Then SB (index 0)
        assert service.get_current_player()["id"] == p_idx0_id
        service.handle_action(p_idx0_id, "call")
        # Then BB (index 1)
        assert service.get_current_player()["id"] == p_idx1_id
        service.handle_action(p_idx1_id, "check")

        assert service.phase == "flop"
        # Flop starts at index 0 (SB)
        assert service.get_current_player()["id"] == p_idx0_id

    def test_refund_all_includes_pot(self):
        """キャンセル時にスタックだけでなくポット内のベット額も返却されるか検証"""
        self.mock_wallet.load_balance.return_value = 10000
        service = TexasPokerService(channel_id=1, bet_amount=100, target_player_count=2)

        p1 = MagicMock(id=1, display_name="P1")
        p2 = MagicMock(id=2, display_name="P2")
        service.add_player(p1)
        service.add_player(p2)

        service.start_game(button_index=0)
        p_first_id = service.get_current_player()["id"]
        service.handle_action(p_first_id, "call")

        service.refund_all()

        payout_calls = self.mock_bet_service.payout.call_args_list
        p1_payout = sum(call.args[1] for call in payout_calls if call.args[0] == 1)
        p2_payout = sum(call.args[1] for call in payout_calls if call.args[0] == 2)

        assert p1_payout == 2000
        assert p2_payout == 2000

    def test_all_in_skips_turns(self):
        """オールインしたプレイヤーの手番が正しくスキップされるか検証"""
        # ID 3 as the small stack player
        self.mock_wallet.load_balance.side_effect = lambda uid: 100 if uid == 3 else 10000
        service = TexasPokerService(channel_id=1, bet_amount=100, target_player_count=3)

        service.add_player(MagicMock(id=1, display_name="P1"))
        service.add_player(MagicMock(id=2, display_name="P2"))
        service.add_player(MagicMock(id=3, display_name="P3"))

        service.start_game(button_index=2)

        # Perform action until Flop
        for _ in range(3):
            curr = service.get_current_player()
            # If ID 3 acts, they might go all-in or call
            if curr["id"] == 3:
                service.handle_action(3, "all_in")
            else:
                service.handle_action(curr["id"], "call")

        assert service.phase == "flop"

        # Verify turn rotation on Flop
        # Identify non-all-in players
        active_ids = [
            p["id"] for p in service.players if not service.player_states[p["id"]].is_all_in
        ]

        # Flop action starts from SB/BB/BTN skipping all-in
        p_start = service.get_current_player()
        assert p_start["id"] in active_ids

        service.handle_action(p_start["id"], "check")
        p_next = service.get_current_player()
        if p_next["id"] != p_start["id"]:
            assert p_next["id"] in active_ids
            service.handle_action(p_next["id"], "check")

        # Since only 2 players are active, and both checked, phase should advance
        assert service.phase == "turn"

    def test_side_pot_protection(self):
        """ショートオールインしたプレイヤーの配当が制限されるか検証"""
        self.mock_wallet.load_balance.side_effect = lambda uid: 100 if uid == 1 else 1000
        service = TexasPokerService(channel_id=1, bet_amount=100, target_player_count=3)

        service.add_player(MagicMock(id=1, display_name="P1"))
        service.add_player(MagicMock(id=2, display_name="P2"))
        service.add_player(MagicMock(id=3, display_name="P3"))

        service.start_game(button_index=2)

        # Pre-flop action
        for _ in range(3):
            p = service.get_current_player()
            service.handle_action(p["id"], "call")

        # Flop action
        assert service.phase == "flop"
        # Find active (not all-in) players to act
        for _ in range(2):
            p = service.get_current_player()
            if not service.player_states[p["id"]].is_all_in:
                # One raises, another calls
                if service.current_max_bet == 0:
                    service.handle_action(p["id"], "raise", 500)
                else:
                    service.handle_action(p["id"], "call")
            else:
                # Should not happen as we expect skip
                pass

        # Setup winning cards for ID 1 (all-in player)
        service.community_cards = [("♠", "A"), ("♣", "A"), ("♥", "A"), ("♦", "J"), ("♠", "10")]
        service.player_states[1].hole_cards = [("♦", "A"), ("♥", "A")]  # Quads
        service.player_states[2].hole_cards = [("♠", "2"), ("♣", "3")]
        service.player_states[3].hole_cards = [("♥", "4"), ("♦", "5")]

        results, rake = service.settle_game()
        p1_res = next(r for r in results if r["id"] == 1)
        # Contribution was 100. Payout should be 100 * 3 players = 300.
        assert p1_res["payout"] == 300

    def test_monster_ai_cheat(self):
        """MonsterAIがチート発動時にエラーなく手札が入れ替わるか検証"""
        from logic.poker.ai.brains import MonsterAI

        self.mock_wallet.load_balance.return_value = 10000
        self.mock_bet_service.escrow.return_value = True

        with unittest.mock.patch(
            "logic.bet_service.BetService.get_user_status", return_value="Prime"
        ):
            service = TexasPokerService(channel_id=1, bet_amount=100)
            service.add_player(MagicMock(id=1, display_name="Human"))
            service.start_game(button_index=0)

            monster_p = None
            for p in service.player_states.values():
                if p.is_npc:
                    p.ai_rank = "monster"
                    monster_p = p
                    break

            if not monster_p:
                pytest.skip("NPC not added")

            service.community_cards = [["♠", "2"], ["♠", "10"], ["♠", "K"], ["♦", "5"], ["♣", "9"]]
            # Human has A pair
            human_p = service.player_states[1]
            human_p.hole_cards = [["♥", "A"], ["♦", "A"]]
            # AI has low cards
            monster_p.hole_cards = [["♣", "7"], ["♦", "8"]]

            ai = MonsterAI(monster_p)
            rank_old, _, _ = PokerRules.get_best_hand(
                [tuple(c) for c in monster_p.hole_cards]
                + [tuple(c) for c in service.community_cards]
            )

            with unittest.mock.patch("logic.poker.ai.brains.random.random", return_value=1.0):
                ai.cheat_hand(service)

            rank_new, _, _ = PokerRules.get_best_hand(
                [tuple(c) for c in monster_p.hole_cards]
                + [tuple(c) for c in service.community_cards]
            )
            assert rank_new > rank_old
            assert len(monster_p.hole_cards) == 2
