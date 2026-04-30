import random

from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.dob_shop.dob_shop_effect_manager import DobumonShopEffectManager
from logic.dobumon.genetics.dob_taboo import TabooLogic


class BattleCalculator:
    """
    ダメージ計算や命中判定などの純粋な数学ロジックを担当するクラス。
    """

    @staticmethod
    def calculate_damage(attacker: Dobumon, defender: Dobumon, skill_power: int = 50) -> dict:
        """
        ダメージ計算を実行します。
        Base = (Atk * Atk / (Atk + Def)) * (Power / 50)
        """
        # 攻撃者および防御者それぞれの補正を取得
        a_mods = TabooLogic.get_combat_modifiers(attacker, defender)
        d_mods = TabooLogic.get_combat_modifiers(defender, attacker)

        atk = max(1, attacker.atk * a_mods["atk"])
        df = max(1, defender.defense * d_mods["defense"])

        # ショップアイテム効果の集計 (EffectManagerを利用)
        a_shop = DobumonShopEffectManager.get_combat_modifiers(attacker)
        d_shop = DobumonShopEffectManager.get_combat_modifiers(defender)

        atk *= a_shop["atk"]
        df *= d_shop["defense"]

        # 基本ダメージ (比率式)
        base_dmg = (atk * atk) / (atk + df)

        # 技の威力補正 (通常攻撃は50)
        power_multiplier = skill_power / 50.0

        damage = base_dmg * power_multiplier

        # 属性相性 (火>草>水>火)
        attr_multiplier = 1.0
        attr_map = {"fire": "grass", "grass": "water", "water": "fire"}
        if attr_map.get(attacker.attribute) == defender.attribute:
            attr_multiplier = 1.5
        elif attr_map.get(defender.attribute) == attacker.attribute:
            attr_multiplier = 0.75

        damage *= attr_multiplier

        # クリティカル判定 (5%)
        is_critical = random.random() < 0.05
        if is_critical:
            damage *= 1.3

        # 乱数分散 (±10%)
        variance = random.uniform(0.9, 1.1)
        damage *= variance

        final_damage = max(1, int(damage))

        return {
            "damage": final_damage,
            "is_critical": is_critical,
            "attr_multiplier": attr_multiplier,
        }

    @staticmethod
    def calculate_hit_chance(
        attacker: Dobumon, defender: Dobumon, skill_accuracy: int = 100
    ) -> float:
        """
        命中率を計算します。
        速度(spd) と 回避(eva) の比率に基づきます。
        """
        # 攻撃者および防御者それぞれの補正を取得
        a_mods = TabooLogic.get_combat_modifiers(attacker, defender)
        d_mods = TabooLogic.get_combat_modifiers(defender, attacker)

        spd = max(1, attacker.spd * a_mods["spd"])
        eva = max(0, defender.eva * d_mods["eva"])

        # ショップアイテム効果の集計 (EffectManagerを利用)
        a_shop = DobumonShopEffectManager.get_combat_modifiers(attacker)
        d_shop = DobumonShopEffectManager.get_combat_modifiers(defender)

        spd *= a_shop["spd"]
        eva *= d_shop["eva"]

        # 基本命中率 (spd と eva のバランス)
        # eva が spd と同等の時、命中率は 0.75 程度
        base_hit = 1.0 - (eva / (spd + eva) * 0.5)

        # 技の命中率補正
        final_hit = base_hit * (skill_accuracy / 100.0)

        # 最低保証 30%
        return max(0.3, final_hit)

    @staticmethod
    def check_hit(attacker: Dobumon, defender: Dobumon, skill_accuracy: int = 100) -> bool:
        """
        命中判定を行います。
        """
        chance = BattleCalculator.calculate_hit_chance(attacker, defender, skill_accuracy)
        return random.random() < chance
