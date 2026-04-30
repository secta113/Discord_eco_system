import random
from typing import Dict

from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.core.dob_traits import TraitRegistry

from .dob_train_config import SCALE_FACTORS


class WildGrowthEngine:
    """
    野生戦勝利時の成長（経験値獲得）計算を司るエンジン。
    """

    @staticmethod
    def calculate_gains(dobu: Dobumon, exp_multiplier: float = 1.0) -> Dict[str, float]:
        """
        勝利時にランダムに3つのステータスを選出し、上昇量を計算します。
        トレーニングと同等の成長計算式を使用します。
        """
        all_stats = ["hp", "atk", "defense", "eva", "spd"]
        selected_stats = random.sample(all_stats, 3)

        # トレーニングの1セッションに近い「力」を配分
        # 3つのステータスそれぞれに対し、独立して計算
        base_unit_gain = 0.4 * exp_multiplier  # ランク倍率を適用

        gains = {}
        for stat in selected_stats:
            iv_val = dobu.iv.get(stat, 1.0)

            # 収穫逓減 (成長鈍化) の取得
            # TrainingEngine._get_growth_multiplier を参考に直接計算
            current_val = getattr(dobu, stat, 0.0)
            eff = 1.0 / (1.0 + pow(current_val / 500, 2))
            growth_deg = max(0.2, eff)

            # 特性による補正
            for t in dobu.traits:
                growth_deg = TraitRegistry.get(t).on_growth_multiplier(growth_deg)

            # 乱数 (80% ~ 120%)
            variance = random.uniform(0.8, 1.2)

            # SPD補正
            spd_mod = 0.5 if stat == "spd" else 1.0

            # 最終計算
            gain = (
                base_unit_gain
                * SCALE_FACTORS.get(stat, 1.0)
                * iv_val
                * growth_deg
                * variance
                * spd_mod
                * dobu.growth_multiplier  # ライフステージによる倍率
            )

            gains[stat] = round(max(0.01, gain), 2)

        return gains

    @staticmethod
    def apply_gains(dobu: Dobumon, gains: Dict[str, float]):
        """
        算出された上昇量を Dobumon オブジェクトに適用します。
        """
        for stat, gain in gains.items():
            current_val = getattr(dobu, stat)
            setattr(dobu, stat, round(max(1.0, current_val + gain), 2))
