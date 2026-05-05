from .base import BaseMutationTrait


class GoldHornTrait(BaseMutationTrait):
    key = "gold_horn"
    desc = "金角: 威厳により勝利報酬が1.1倍に増加する (+物理防御)"
    def_mod = 1.2
    reward_mod = 1.1


class RedBackTrait(BaseMutationTrait):
    key = "red_back"
    desc = "赤背: 激しい闘争本能により攻撃力が大幅に上昇する"
    atk_mod = 1.3


class OddEyeTrait(BaseMutationTrait):
    key = "odd_eye"
    desc = "妖眼: 異なる次元を視る瞳。回避率と命中率が向上する"
    eva_mod = 1.3


class BlueBloodTrait(BaseMutationTrait):
    key = "blue_blood"
    desc = "青血: 高貴なエイリアン・ブラッド。HPと生命力が極めて高い"
    hp_mod = 1.3
    illness_mod = 0.5


class GlassBladeTrait(BaseMutationTrait):
    key = "glass_blade"
    desc = "硝子の刃: HPと防御力が半減する代わりに、攻撃力と速度が2.5倍になる狂気の刃"
    hp_mod = 0.5
    def_mod = 0.5
    atk_mod = 2.5
    spd_mod = 2.5
