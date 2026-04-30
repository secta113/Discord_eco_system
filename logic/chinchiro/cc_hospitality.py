import random
from typing import List, Optional, Tuple

from core.utils.logger import Logger
from logic.bet_service import BetService
from logic.economy.game_logic import GameLogicService

from .cc_rules import ChinchiroRules


class ChinchiroHospitality:
    """チンチロリン専用の接待（目なし回避）ロジック"""

    @staticmethod
    def apply_roll_protection(
        user_id: int, current_roll_count: int, dice: List[int], status_rank: Optional[str] = None
    ) -> Tuple[List[int], bool]:
        """
        3投目で目なしの場合、一定確率で介入する。
        戻り値: (最終的なダイス, 接待が発動したか)
        """
        role_name, strength = ChinchiroRules.calculate_role(dice)

        if strength <= 0 and current_roll_count == 3:
            h_rate = GameLogicService.get_hospitality_rate(user_id, status_rank=status_rank)
            if random.random() < h_rate:
                if status_rank is None:
                    status_rank = BetService.get_user_status(user_id)
                Logger.info(
                    "Economy",
                    f"[HOSPITALITY_TRIGGERED] user:{user_id} status:{status_rank} outcome:rerolled (Chinchiro)",
                )

                # 初回のリロール
                new_dice = [random.randint(1, 6) for _ in range(3)]
                _, new_strength = ChinchiroRules.calculate_role(new_dice)

                # リロールしても目なしの場合、強制的に「○の目」を付与
                if new_strength <= 0:
                    p = random.randint(1, 6)
                    x = (p % 6) + 1
                    new_dice = [x, x, p]

                return new_dice, True

        return dice, False
