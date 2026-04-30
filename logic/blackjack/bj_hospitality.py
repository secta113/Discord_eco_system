import random
from typing import List, Optional

from core.utils.logger import Logger
from logic.bet_service import BetService
from logic.economy.game_logic import GameLogicService

from .bj_deck import Deck
from .bj_models import BlackjackHand


class BlackjackHospitality:
    """ブラックジャック専用の接待（バッドラック回避）ロジック"""

    @staticmethod
    def apply_hit_protection(
        deck: Deck, user_id: int, hand: BlackjackHand, status_rank: Optional[str] = None
    ) -> bool:
        """
        プレイヤーのHit時にバーストしそうな場合、確率で回避させる。
        戻り値: 接待が発動したかどうか
        """
        score_before = hand.score
        # 12-16の間が最もバーストしやすい
        if 12 <= score_before <= 16:
            next_card = deck.peek()
            if next_card and score_before + Deck.VALUES[next_card[1]] > 21:
                h_rate = GameLogicService.get_hospitality_rate(user_id, status_rank=status_rank)
                if random.random() < h_rate:
                    if status_rank is None:
                        status_rank = BetService.get_user_status(user_id)
                    Logger.info(
                        "Economy",
                        f"[HOSPITALITY_TRIGGERED] user:{user_id} status:{status_rank} outcome:bust_avoided (Blackjack)",
                    )
                    deck.move_top_to_bottom()
                    hand.hospitality_triggered = True
                    return True
        return False

    @staticmethod
    def apply_dealer_bust_induction(deck: Deck, players: List[dict], dealer_score: int) -> bool:
        """
        ディーラーが12-16の場合、確率で10を引かせてバーストさせる。
        """
        if 12 <= dealer_score <= 16:
            next_card = deck.peek()
            if not next_card:
                return False

            next_score = dealer_score + Deck.VALUES[next_card[1]]
            if next_card[1] == "A" and dealer_score <= 10:
                next_score += 10

            # 次のカードでディーラーが17-21（スタンド）に収まる場合、
            # 確率でそれを10点のカードと入れ替えてバーストを誘導する
            if 17 <= next_score <= 21:
                # プレイヤーの中で最も高い接待レートを適用する
                h_rate = max(
                    (GameLogicService.get_hospitality_rate(p["id"]) for p in players), default=0.05
                )

                if random.random() < h_rate:
                    if deck.swap_top_with_ten():
                        Logger.info("Economy", "[HOSPITALITY_TRIGGERED] dealer_bust_induced")
                        return True
        return False
