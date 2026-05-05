from typing import Any

from .base import BaseMutationTrait


class SupernovaTrait(BaseMutationTrait):
    key = "supernova"
    desc = "超新星: 個体値の振れ幅が最大となり、次世代の突然変異率を極限まで高める"
    mutation_mod = 5.0
    variation_range = (0.5, 2.5)


class SingularityTrait(BaseMutationTrait):
    key = "singularity"
    desc = (
        "特異点: 絶対不変の完成形。両親の優れた能力を無欠で引き継ぎ、その形を永劫に保つ究極の個体。"
    )
    variation_range = (1.0, 1.0)

    def can_extend_lifespan(self) -> bool:
        return False


class AntiTabooTrait(BaseMutationTrait):
    key = "anti_taboo"
    desc = "対禁忌: 禁忌を討つ者。禁忌深度を持つ相手に対して戦闘能力が向上する"

    def on_combat_start(self, dobumon: Any, opponent: Any) -> dict[str, float]:
        mods = {}
        if "the_forbidden" in opponent.traits:
            # 禁断相手には全ステータス10倍
            return dict.fromkeys(["atk", "defense", "hp", "eva", "spd"], 10.0)

        target_depth = opponent.genetics.get("forbidden_depth", 0)
        if target_depth > 0:
            bonus = 1.0 + (target_depth * 0.3)
            mods["atk"] = bonus
            mods["defense"] = bonus
        return mods
