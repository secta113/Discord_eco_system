from typing import Any, Dict, List

from logic.constants import JPRarity

from .bj_models import BlackjackHand


class BlackjackRules:
    """勝敗判定と配当倍率の定義"""

    PAYOUT_RATIO_BJ = 2.5
    PAYOUT_RATIO_777 = 21
    PAYOUT_RATIO_678 = 5
    PAYOUT_RATIO_6CHARLIE = 7
    PAYOUT_RATIO_WIN = 2
    PAYOUT_RATIO_PUSH = 1

    # 旧仕様（v2.10以前）の比率は参考として残し、使用しない
    JACKPOT_RATIO_777 = 0.30  # EPIC
    JACKPOT_RATIO_678 = 0.03  # COMMON
    JACKPOT_RATIO_6CHARLIE = 0.10  # RARE

    @staticmethod
    def calculate_payout(hand: BlackjackHand, dealer_score: int) -> Dict[str, Any]:
        """
        手札とディーラーのスコアを比較し、配当倍率と結果メッセージを返す。
        戻り値: {
            "payout_multiplier": float,
            "jp_rarity": JPRarity,
            "result_str": str,
            "is_win": bool,
            "is_rare": bool,
            "rare_type": str (777, 678, 6charlie, suited_bj, blackjack)
        }
        """
        score = hand.score
        rare_info = hand.get_rare_hand_info()

        # 特殊役の判定
        if rare_info["is_777"]:
            return {
                "payout_multiplier": BlackjackRules.PAYOUT_RATIO_777,
                "jp_rarity": JPRarity.EPIC,
                "result_str": "🎰 **7-7-7!**",
                "is_win": True,
                "is_rare": True,
                "rare_type": "777",
            }
        if rare_info["is_678"]:
            return {
                "payout_multiplier": BlackjackRules.PAYOUT_RATIO_678,
                "jp_rarity": JPRarity.COMMON,
                "result_str": "🌈 **6-7-8!**",
                "is_win": True,
                "is_rare": True,
                "rare_type": "678",
            }
        if rare_info["is_6charlie"]:
            return {
                "payout_multiplier": BlackjackRules.PAYOUT_RATIO_6CHARLIE,
                "jp_rarity": JPRarity.RARE,
                "result_str": "🏅 **6-Card Charlie!**",
                "is_win": True,
                "is_rare": True,
                "rare_type": "6charlie",
            }

        # 通常のBlackjack
        if hand.status == "blackjack":
            return {
                "payout_multiplier": BlackjackRules.PAYOUT_RATIO_BJ,
                "jp_rarity": JPRarity.NONE,
                "result_str": "🎉 Blackjack! (1.5x)",
                "is_win": True,
                "is_rare": True,
                "rare_type": "suited_bj" if rare_info["is_suited_bj"] else "blackjack",
            }

        # バースト
        if hand.status == "bust":
            return {
                "payout_multiplier": 0,
                "jp_rarity": JPRarity.NONE,
                "result_str": "💥 Bust (負け)",
                "is_win": False,
                "is_rare": False,
                "rare_type": None,
            }

        # ディーラーバースト
        if dealer_score > 21:
            return {
                "payout_multiplier": BlackjackRules.PAYOUT_RATIO_WIN,
                "jp_rarity": JPRarity.NONE,
                "result_str": "🎉 Win (Dealer Bust)",
                "is_win": True,
                "is_rare": False,
                "rare_type": None,
            }

        # 勝ち/負け/プッシュ
        if score > dealer_score:
            return {
                "payout_multiplier": BlackjackRules.PAYOUT_RATIO_WIN,
                "jp_rarity": JPRarity.NONE,
                "result_str": "🎉 Win",
                "is_win": True,
                "is_rare": False,
                "rare_type": None,
            }
        elif score < dealer_score:
            return {
                "payout_multiplier": 0,
                "jp_rarity": JPRarity.NONE,
                "result_str": "💀 Lose",
                "is_win": False,
                "is_rare": False,
                "rare_type": None,
            }
        else:
            return {
                "payout_multiplier": BlackjackRules.PAYOUT_RATIO_PUSH,
                "jp_rarity": JPRarity.NONE,
                "result_str": "🤝 Push",
                "is_win": False,
                "is_rare": False,
                "rare_type": None,
            }
