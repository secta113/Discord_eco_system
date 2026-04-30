from unittest.mock import MagicMock, patch

import pytest

from logic.poker.pk_models import PokerPlayer
from logic.poker.pk_settlement_manager import PokerSettlementManager


def create_mock_player(uid, name, bet, is_npc=False):
    p = PokerPlayer(uid, name, stack=1000, is_npc=is_npc)
    p.total_bet = bet
    p.status = "playing"
    return p


class TestPokerEconomy:
    """
    ポーカーの配当計算、Rake徴収、NPC利益回収、およびジャックポット蓄積の正確性を検証するテストクラス。
    特にインフレ防止ロジック（実入金比率による制限）が正しく機能しているかを重点的にチェックします。
    """

    @patch("logic.poker.pk_settlement_manager.BetService.add_to_jackpot_real_only")
    @patch("logic.poker.pk_settlement_manager.BetService.payout")
    def test_human_winner_economy(self, mock_payout, mock_jp):
        """
        [シナリオ1] 人間が勝利した場合
        検証項目:
        1. Rake 5% が正しく徴収されること。
        2. Rake分から実入金比率のみがJPへ加算されること。
        3. 勝者には「残スタック」と「配当全額(Net)」が支払われること。
        """
        # Pot: 300 (Human: 100, NPC_A: 100, NPC_B: 100)
        p1 = create_mock_player(1, "Human", 100, is_npc=False)
        p1.stack = 500  # テーブルに残った 500 pts
        p2 = create_mock_player(-1, "NPC_A", 100, is_npc=True)
        p3 = create_mock_player(-2, "NPC_B", 100, is_npc=True)

        player_states = {1: p1, -1: p2, -2: p3}

        with patch.object(PokerSettlementManager, "_identify_winners") as mock_id:
            # Pot 300. Rake 5% (15) -> Net 285
            # _identify_winners はすでに Rake が引かれた後の self.pot を見るため、285 を返すはず。
            mock_id.return_value = ([p1], {1: 285}, [p1, p2, p3])

            settler = PokerSettlementManager([], 300)
            results, rake_returned = settler.execute(player_states)

            # Rakeの検証: 15pts (実入金 1/3)
            mock_jp.assert_any_call(15, 300, 100, "Poker Rake")

            # --- 払い戻しの検証 ---
            # 1. 残スタック返還 (500 pts)
            mock_payout.assert_any_call(1, 500, is_pvp=False, reason="ポーカー残スタック返還")
            # 2. 配当額 (Net 285 pts)
            mock_payout.assert_any_call(1, 285, is_pvp=False, reason="ポーカー勝利配当")

    @patch("logic.poker.pk_settlement_manager.BetService.add_to_jackpot_real_only")
    @patch("logic.poker.pk_settlement_manager.BetService.payout")
    def test_npc_winner_economy(self, mock_payout, mock_jp):
        """
        [シナリオ2] NPCが勝利した場合
        """
        p1 = create_mock_player(1, "Human", 100, is_npc=False)
        p1.stack = 400
        p2 = create_mock_player(-1, "NPC_Winner", 100, is_npc=True)
        p3 = create_mock_player(-2, "NPC_B", 100, is_npc=True)

        player_states = {1: p1, -1: p2, -2: p3}

        with patch.object(PokerSettlementManager, "_identify_winners") as mock_id:
            # Net 285 を NPC(p2) が獲得
            mock_id.return_value = ([p2], {-1: 285}, [p1, p2, p3])

            settler = PokerSettlementManager([], 300)
            settler.execute(player_states)

            # 負けた人間(p1)のスタックは返還される
            mock_payout.assert_any_call(1, 400, is_pvp=False, reason="ポーカー残スタック返還")

            # Rake: 15
            mock_jp.assert_any_call(15, 300, 100, "Poker Rake")
            # NPC Profit: (Net 285 - Bet 100 = 185)
            mock_jp.assert_any_call(185, 300, 100, "Poker NPC Profit")

    @patch("logic.poker.pk_settlement_manager.BetService.add_to_jackpot_real_only")
    def test_all_npc_economy(self, mock_jp):
        """
        [シナリオ3] 全員NPCの場合
        """
        p1 = create_mock_player(-1, "NPC_A", 100, is_npc=True)
        p2 = create_mock_player(-2, "NPC_B", 100, is_npc=True)
        player_states = {-1: p1, -2: p2}

        with patch.object(PokerSettlementManager, "_identify_winners") as mock_id:
            # Net 190 (200 - 10 rake)
            mock_id.return_value = ([p1], {-1: 190}, [p1, p2])
            settler = PokerSettlementManager([], 200)
            settler.execute(player_states)

            # Rake: 10 (実入金 0)
            mock_jp.assert_any_call(10, 200, 0, "Poker Rake")
            # NPC Profit: (190 - 100 = 90) (実入金 0)
            mock_jp.assert_any_call(90, 200, 0, "Poker NPC Profit")

    @patch("logic.poker.pk_settlement_manager.BetService.add_to_jackpot_real_only")
    @patch("logic.poker.pk_settlement_manager.BetService.payout")
    def test_split_pot_economy(self, mock_payout, mock_jp):
        """
        [シナリオ4] スプリットポット（人間2名）
        """
        p1 = create_mock_player(1, "H_A", 100, is_npc=False)
        p1.stack = 0
        p2 = create_mock_player(2, "H_B", 100, is_npc=False)
        p2.stack = 0
        player_states = {1: p1, 2: p2}

        with patch.object(PokerSettlementManager, "_identify_winners") as mock_id:
            # Pot 200. Rake 10 -> Net 190. 各自 95 pts 獲得
            mock_id.return_value = ([p1, p2], {1: 95, 2: 95}, [p1, p2])

            settler = PokerSettlementManager([], 200)
            settler.execute(player_states)

            # 人間が2名なので is_pvp=True
            mock_payout.assert_any_call(1, 95, is_pvp=True, reason="ポーカー勝利配当")
            mock_payout.assert_any_call(2, 95, is_pvp=True, reason="ポーカー勝利配当")
