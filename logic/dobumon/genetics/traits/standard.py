from .base import BaseMutationTrait


class EarlyTrait(BaseMutationTrait):
    key = "early"
    desc = "早熟: 初期値が高いが、後半の伸びが鈍い"
    hp_mod = 1.2
    growth_mod = 0.8


class LateTrait(BaseMutationTrait):
    key = "late"
    desc = "晩成: 初期値は低いが、限界突破しやすい"
    hp_mod = 0.8
    growth_mod = 1.5


class HardyTrait(BaseMutationTrait):
    key = "hardy"
    desc = "金剛: 病気になりにくく、タフである"
    illness_mod = 0.5
    lifespan_mod = 1.2

    def get_consumption_multiplier(self) -> float:
        return 0.7


class FrailTrait(BaseMutationTrait):
    key = "frail"
    desc = "繊細: 病気になりやすいが、感性が鋭い"
    illness_mod = 2.0
    eva_mod = 1.2

    def get_consumption_multiplier(self) -> float:
        return 1.5


class StableTrait(BaseMutationTrait):
    key = "stable"
    desc = "安定: ステータスの振れ幅が小さい"
    variation_range = (0.95, 1.05)


class BurstTrait(BaseMutationTrait):
    key = "burst"
    desc = "爆発: 突然変異や大成功が起きやすい"
    mutation_mod = 2.0
    great_success_mod = 2.0


class AestheticTrait(BaseMutationTrait):
    key = "aesthetic"
    desc = "美形: 端麗な容姿。回避率がわずかに高い"
    eva_mod = 1.05
