import unittest.mock
from unittest.mock import MagicMock

import pytest

from core.utils.constants import GameType, JPRarity
from logic.poker.pk_models import PokerPlayer
from logic.poker.pk_rules import PokerRules
from logic.poker.pk_settlement_manager import PokerSettlementManager


class TestPokerJackpotFold:
    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        with (
            unittest.mock.patch("core.economy.wallet.update_stats") as mock_update_stats,
            unittest.mock.patch(
                "logic.bet_service.BetService.add_to_jackpot_real_only"
            ) as mock_add_jp,
            unittest.mock.patch("logic.bet_service.BetService.execute_jackpot") as mock_execute_jp,
            unittest.mock.patch("logic.bet_service.BetService.payout") as mock_payout,
        ):
            self.mock_update_stats = mock_update_stats
            self.mock_add_jp = mock_add_jp
            self.mock_execute_jp = mock_execute_jp
            self.mock_payout = mock_payout

            # 初期設定
            self.mock_execute_jp.return_value = 50000  # JP配当が発生したと仮定
            self.mock_payout.side_effect = lambda uid, amt, **kwargs: amt
            yield

    def test_jackpot_awarded_on_fold_win(self):
        """
        全員フォールドによる不戦勝時でも、勝者が強い役（ロイヤルフラッシュ等）を持っていれば
        ジャックポットが発生することを検証する。
        """
        # 1. 場のセットアップ (ロイヤルフラッシュができるコミュニティカード)
        community_cards = [
            ("spade", "10"),
            ("spade", "J"),
            ("spade", "Q"),
            ("heart", "2"),
            ("diamond", "5"),
        ]
        pot = 10000

        # 2. プレイヤーの状態をセットアップ
        # 勝者 (スペードのA, K を所持 -> ロイヤルフラッシュ)
        winner = PokerPlayer(user_id=1, name="WinnerUser", stack=2000)
        winner.hole_cards = [("spade", "A"), ("spade", "K")]
        winner.status = "playing"
        winner.total_bet = 500

        # 敗者 (フォールド)
        loser = PokerPlayer(user_id=2, name="LoserUser", stack=1500)
        loser.status = "folded"
        loser.total_bet = 500

        player_states = {1: winner, 2: loser}

        # 3. 決済実行
        manager = PokerSettlementManager(community_cards, pot)
        settle_details, rake = manager.execute(player_states)

        # 4. 検証
        # 勝者は1人
        assert len(settle_details) == 1
        res = settle_details[0]
        assert res["id"] == 1
        assert res["hand"] == "ロイヤルフラッシュ"

        # 重要：不戦勝でも execute_jackpot が呼ばれていること
        self.mock_execute_jp.assert_called_once()
        args = self.mock_execute_jp.call_args[0]
        assert args[0] == 1  # user_id
        assert args[1] == GameType.POKER
        assert args[2] == JPRarity.LEGENDARY  # ロイヤルフラッシュなのでLEGENDARY

        # 配当の詳細にJOD(JP)が含まれていること
        assert res["jp_payout"] == 50000
        assert res["profit"] > 50000  # 純利益にJPが含まれる

    def test_no_jackpot_on_fold_win_with_weak_hand(self):
        """
        不戦勝時でも、手が弱い（ハイカード等）場合はジャックポットが発生しないことを検証。
        """
        community_cards = [
            ("spade", "2"),
            ("heart", "4"),
            ("diamond", "6"),
            ("club", "8"),
            ("spade", "10"),
        ]
        pot = 1000

        winner = PokerPlayer(user_id=1, name="WinnerUser", stack=1000)
        winner.hole_cards = [("heart", "Q"), ("diamond", "7")]  # ハイカード
        winner.status = "playing"

        loser = PokerPlayer(user_id=2, name="LoserUser", stack=1000)
        loser.status = "folded"

        player_states = {1: winner, 2: loser}

        manager = PokerSettlementManager(community_cards, pot)
        settle_details, _ = manager.execute(player_states)

        # 役名が正しく判定されていること (以前は "不戦勝" 固定だった箇所)
        assert settle_details[0]["hand"] == "不戦勝 (相手フォールド)"
        # ※注: 実装時に不戦勝メッセージを残すか、役名に書き換えるかは検討の余地あり。
        # 今回の計画では evaluate_5_cards を走らせるため、内部ランクは計算されるが
        # メッセージ表示は「不戦勝」のままでもJP判定さえ走ればOK。

        # ジャックポットは呼ばれないはず
        self.mock_execute_jp.assert_not_called()
        assert settle_details[0]["jp_payout"] == 0
