from typing import Dict, List, Optional, Tuple

from core.economy import wallet
from core.utils.logger import Logger
from logic.bet_service import BetService
from logic.constants import GameType, JPRarity

from .pk_models import PokerPlayer
from .pk_rules import PokerRules


class PokerSettlementManager:
    """
    ポーカーの決着、勝敗判定、配当実行を担当するクラス。
    """

    RAKE_RATE = 0.05

    def __init__(self, community_cards: List[Tuple[str, str]], pot: int):
        self.community_cards = community_cards
        self.pot = pot
        self.total_rake_collected = 0

    def execute(self, player_states: Dict[int, PokerPlayer]) -> Tuple[List[Dict], int]:
        """
        全プレイヤーの状態を精査し、勝敗判定と配当処理を実行する。
        戻り値: (UI表示用の勝者リスト, 徴収されたRake合計)
        """
        # インフレ抑制：実入金（人間プレイヤーの賭け金合計）を算出
        self.real_pot = sum(p.total_bet for p in player_states.values() if not p.is_npc)
        self.original_pot = self.pot

        # ハウスエッジ（手数料）の徴収
        rake_amount = int(self.pot * self.RAKE_RATE)
        if rake_amount > 0:
            # 実入金比率の分だけJPへ追加（仮想マネーは回収しない）
            actual_rake = BetService.add_to_jackpot_real_only(
                rake_amount, self.original_pot, self.real_pot, "Poker Rake"
            )
            self.total_rake_collected = rake_amount
            self.pot -= rake_amount
            Logger.info(
                "Poker",
                f"Rake processed: {rake_amount} pts (Actual JP: {actual_rake} pts)",
            )

        winners, payout_map, active_players = self._identify_winners(player_states)
        if not active_players:
            return [], self.total_rake_collected

        settle_details = []
        is_single_active = len(active_players) == 1
        is_pvp_game = sum(1 for p in player_states.values() if not p.is_npc) >= 2

        for p in player_states.values():
            is_winner = any(w.user_id == p.user_id for w in winners)

            # ジャックポット・統計・手役名の取得
            payout_for_this = payout_map.get(p.user_id, 0)
            hand_name, _, jp_payout = self._handle_jackpot_and_stats(
                p, is_winner, is_single_active, payout_for_this
            )

            # 実際の送金
            paid_stack, paid_win = self._execute_payouts(p, is_winner, payout_for_this, is_pvp_game)

            if is_winner:
                settle_details.append(
                    {
                        "id": p.user_id,
                        "name": p.name,
                        "payout": paid_stack + paid_win + jp_payout,
                        "hand": hand_name,
                        "profit": paid_win + jp_payout,
                        "jp_payout": jp_payout,
                    }
                )

        return settle_details, self.total_rake_collected

    def _identify_winners(
        self, player_states: Dict[int, PokerPlayer]
    ) -> Tuple[List[PokerPlayer], Dict[int, int], List[PokerPlayer]]:
        active_players = [p for p in player_states.values() if p.status != "folded"]
        if not active_players:
            return [], {}, []

        if len(active_players) == 1:
            winner = active_players[0]
            # 不戦勝時も手札を評価して、ジャックポット判定や統計表示に備える
            rank, strength, name = PokerRules.get_best_hand(
                winner.hole_cards + self.community_cards
            )
            winner.final_hand_name = name
            winner.final_rank = rank
            return [winner], {winner.user_id: self.pot}, active_players

        # ショウダウン判定
        best_strength = None
        winners = []
        for p in active_players:
            rank, strength, name = PokerRules.get_best_hand(p.hole_cards + self.community_cards)
            p.final_hand_name = name
            p.final_rank = rank

            if best_strength is None or (rank, strength) > (best_strength[0], best_strength[1]):
                best_strength = (rank, strength)
                winners = [p]
            elif (rank, strength) == best_strength:
                winners.append(p)

        payout_per_winner = self.pot // len(winners)
        payout_map = {}
        num_active = len(player_states)  # 全参加者数（既存ロジックに合わせる）

        for w in winners:
            # 自分が賭けた額の全参加者数倍が獲得上限（簡易サイドポット対応）
            max_payout = w.total_bet * num_active
            payout_map[w.user_id] = min(payout_per_winner, max_payout)

        return winners, payout_map, active_players

    def _handle_jackpot_and_stats(
        self, p: PokerPlayer, is_winner: bool, is_single_active: bool, payout_per_winner: int
    ) -> Tuple:
        hand_name = "フォールド"
        profit = 0

        if is_winner:
            profit = payout_per_winner
            if not p.is_npc:
                wallet.update_stats(p.user_id, True, profit)

            rarity = self._get_jp_rarity(p.final_rank)
            hand_name = p.final_hand_name or "不明"
            if is_single_active and rarity == JPRarity.NONE:
                hand_name = "不戦勝 (相手フォールド)"

            # ジャックポット判定 (NPCは対象外)
            jp_payout = 0
            if not p.is_npc:
                rarity = self._get_jp_rarity(p.final_rank)
                if rarity != JPRarity.NONE:
                    jp_payout = BetService.execute_jackpot(
                        p.user_id, GameType.POKER, rarity, p.final_hand_name or "不明"
                    )
            return hand_name, profit + jp_payout, jp_payout
        else:
            if not p.is_npc:
                wallet.update_stats(p.user_id, False, p.total_bet)
            if p.status != "folded":
                hand_name = p.final_hand_name or "不明"
            return hand_name, 0, 0

    def _get_jp_rarity(self, final_rank: Optional[int]) -> JPRarity:
        if final_rank == PokerRules.HAND_RANK_ROYAL_FLUSH:
            return JPRarity.LEGENDARY
        elif final_rank == PokerRules.HAND_RANK_STRAIGHT_FLUSH:
            return JPRarity.EPIC
        elif final_rank == PokerRules.HAND_RANK_FOUR_OF_A_KIND:
            return JPRarity.RARE
        return JPRarity.NONE

    def _execute_payouts(
        self, p: PokerPlayer, is_winner: bool, payout_per_winner: int, is_pvp_game: bool
    ) -> Tuple:
        paid_stack = 0
        if p.stack > 0:
            if p.is_npc:
                # NPCの残スタックはシステム（Jackpot）へ入れずにそのまま消滅させる（インフレ抑制）
                # paid_stack は統計表示用にセットだけしておく
                paid_stack = p.stack
            else:
                paid_stack = BetService.payout(
                    p.user_id, p.stack, is_pvp=False, reason="ポーカー残スタック返還"
                )

        paid_win = 0
        if is_winner:
            if p.is_npc:
                # NPCの純粋な勝ち分を実入金比率に基づいてJackpotへ
                # 無から生み出したスタック自体の返還分は Jackpot に入れない（無限増殖防止）
                profit = payout_per_winner - p.total_bet
                if profit > 0:
                    BetService.add_to_jackpot_real_only(
                        profit, self.original_pot, self.real_pot, "Poker NPC Profit"
                    )
                paid_win = payout_per_winner
            else:
                paid_win = BetService.payout(
                    p.user_id, payout_per_winner, is_pvp=is_pvp_game, reason="ポーカー勝利配当"
                )
        return paid_stack, paid_win
