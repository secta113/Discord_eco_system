from typing import Any

from .base import BaseMutationTrait


class UnlimitedTrait(BaseMutationTrait):
    key = "unlimited"
    desc = "無限: 成長の限界を超越し、育成時のステータス減衰を無視する"
    growth_mod = 1.5

    def on_growth_multiplier(self, dobumon: Any, current_multiplier: float) -> float:
        # 減衰を無視して最低 1.0 を維持する
        return max(1.0, current_multiplier * self.growth_mod)


class ParasiticTrait(BaseMutationTrait):
    key = "parasitic"
    desc = "捕食: 普段ステータスが伸びないが戦闘時等で飛躍的に成長・報酬を得る"

    def on_growth_multiplier(self, dobumon: Any, current_multiplier: float) -> float:
        return current_multiplier * 0.1

    def on_combat_reward(self, exp_gain: float, pt_reward: int) -> tuple[float, int]:
        return exp_gain * 3.0, int(pt_reward * 3.0)
