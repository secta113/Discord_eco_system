from .base import BaseMutationTrait


class UndeadTrait(BaseMutationTrait):
    key = "undead"
    desc = "不死: 死の概念がない。寿命が極めて長く病気にならず、敗北ロストを無効化する"
    lifespan_mod = 5.0
    illness_mod = 0.0

    def get_consumption_multiplier(self) -> float:
        # 不死は老化も極めて遅い
        return 0.2

    def modifies_battle_death(self) -> bool:
        return True


class CrystalizedTrait(BaseMutationTrait):
    key = "crystalized"
    desc = "結晶化: 硬いが脆いガラスの盾。病気にならないがHPが極端に低い"
    def_mod = 2.0
    hp_mod = 0.5
    illness_mod = 0.0


class ChimeraTrait(BaseMutationTrait):
    key = "chimera"
    desc = "合成獣: 無尽蔵の体力を持つが、拒絶反応により常に重病に苛まれる"
    hp_mod = 2.5
    illness_mod = 3.0
