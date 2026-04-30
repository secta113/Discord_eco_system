from typing import Any, Dict, Tuple

# 相互参照を避けるため、遅延インポートまたはパッケージ内インポートを使用
from logic.dobumon.genetics.dob_genetics_constants import TRAIT_EFFECTS


class BaseTrait:
    """特性の基本クラス（Strategyパターン）"""

    def __init__(self, key: str, config: Dict[str, Any]):
        self.key = key
        self.desc = config.get("desc", "")
        self.hp_mod = config.get("hp_mod", 1.0)
        self.atk_mod = config.get("atk_mod", 1.0)
        self.def_mod = config.get("def_mod", 1.0)
        self.eva_mod = config.get("eva_mod", 1.0)
        self.spd_mod = config.get("spd_mod", 1.0)
        self.illness_mod = config.get("illness_mod", 1.0)
        self.lifespan_mod = config.get("lifespan_mod", 1.0)
        self.growth_mod = config.get("growth_mod", 1.0)
        self.reward_mod = config.get("reward_mod", 1.0)
        self.mutation_mod = config.get("mutation_mod", 1.0)
        self.great_success_mod = config.get("great_success_mod", 1.0)
        self.variation_range = config.get("variation_range", None)

    def modifies_battle_death(self) -> bool:
        """戦闘での死亡を無効化するか"""
        return False

    def on_growth_multiplier(self, current_multiplier: float) -> float:
        """トレーニングの成長減衰に介入する"""
        return current_multiplier

    def on_inherit_allele(self) -> str:
        """次世代へ引き継ぐ直前にアレルを書き換える場合、そのアレル名を返す"""
        return self.key

    def on_combat_reward(self, exp_gain: float, pt_reward: int) -> Tuple[float, int]:
        """戦闘での獲得報酬に介入する"""
        return exp_gain * self.reward_mod, int(pt_reward * self.reward_mod)

    def get_stat_multiplier(self, stat_name: str) -> float:
        """特定のステータス倍率を返します"""
        return getattr(self, f"{stat_name}_mod", 1.0)


class UndeadTrait(BaseTrait):
    def modifies_battle_death(self) -> bool:
        return True


class UnlimitedTrait(BaseTrait):
    def on_growth_multiplier(self, current_multiplier: float) -> float:
        return max(1.0, current_multiplier)


class ParasiticTrait(BaseTrait):
    def on_growth_multiplier(self, current_multiplier: float) -> float:
        return current_multiplier * 0.1

    def on_combat_reward(self, exp_gain: float, pt_reward: int) -> Tuple[float, int]:
        return exp_gain * 3.0, int(pt_reward * 3.0)


class SingularityTrait(BaseTrait):
    pass


class TraitRegistry:
    """全特性の一元管理レジストリ"""

    _traits: Dict[str, BaseTrait] = {}
    _initialized: bool = False

    @classmethod
    def register(cls, key: str, config: Dict[str, Any], trait_class=BaseTrait):
        cls._traits[key] = trait_class(key, config)

    @classmethod
    def get(cls, key: str) -> BaseTrait:
        if not cls._initialized:
            cls.initialize()
        return cls._traits.get(key, BaseTrait(key, {}))

    @classmethod
    def initialize(cls):
        """定数データからレジストリを初期化。"""
        if cls._initialized:
            return

        class_map = {
            "undead": UndeadTrait,
            "unlimited": UnlimitedTrait,
            "parasitic": ParasiticTrait,
            "singularity": SingularityTrait,
        }

        for key, conf in TRAIT_EFFECTS.items():
            t_class = class_map.get(key, BaseTrait)
            cls.register(key, conf, t_class)

        cls._initialized = True
