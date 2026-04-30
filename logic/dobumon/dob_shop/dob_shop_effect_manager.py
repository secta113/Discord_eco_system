from typing import Any, Dict, List, Optional, Tuple

from logic.dobumon.core.dob_models import Dobumon


class DobumonShopEffectManager:
    """
    ドブモンのショップアイテムによる各種ゲーム内効果を計算・集約するエンジン。
    """

    @staticmethod
    def get_breeding_bonuses(p1: Dobumon, p2: Dobumon) -> Dict[str, Any]:
        """
        両親のショップフラグから交配時の各種補正値を計算します。
        """
        iv_bonus_base = 0.0
        # 生贄の刻印 (両親分累積)
        if "sacrifice_mark" in p1.shop_flags:
            iv_bonus_base += p1.shop_flags["sacrifice_mark"].get("iv_bonus", 0.0)
        if "sacrifice_mark" in p2.shop_flags:
            iv_bonus_base += p2.shop_flags["sacrifice_mark"].get("iv_bonus", 0.0)

        # 特異点の断片 (両親分累積、最強ステータスにのみ適用)
        high_iv_bonus = 0.0
        if "singularity_fragment" in p1.shop_flags:
            high_iv_bonus += p1.shop_flags["singularity_fragment"].get("iv_bonus", 0.0)
        if "singularity_fragment" in p2.shop_flags:
            high_iv_bonus += p2.shop_flags["singularity_fragment"].get("iv_bonus", 0.0)

        # 突然変異率上昇 (ミューテーション・ゲノム)
        mutation_chance_delta = 0.0
        if "mutation_genome" in p1.shop_flags:
            mutation_chance_delta += p1.shop_flags["mutation_genome"].get("chance_delta", 0.0)
        if "mutation_genome" in p2.shop_flags:
            mutation_chance_delta += p2.shop_flags["mutation_genome"].get("chance_delta", 0.0)

        # 禁忌深度への加算値 (生贄の刻印)
        taboo_depth_add = 0
        if "sacrifice_mark" in p1.shop_flags:
            taboo_depth_add += p1.shop_flags["sacrifice_mark"].get("taboo_add", 0)
        if "sacrifice_mark" in p2.shop_flags:
            taboo_depth_add += p2.shop_flags["sacrifice_mark"].get("taboo_add", 0)

        # 性別固定バイアス (粗悪な性別固定カプセル)
        gender_bias_m_chance = 0.0
        gender_bias_f_chance = 0.0

        if "bad_gender_fix_m" in p1.shop_flags:
            gender_bias_m_chance = p1.shop_flags["bad_gender_fix_m"].get("chance", 0.0)
            iv_bonus_base += p1.shop_flags["bad_gender_fix_m"].get("iv_penalty", 0.0)
        if "bad_gender_fix_m" in p2.shop_flags:
            gender_bias_m_chance = p2.shop_flags["bad_gender_fix_m"].get("chance", 0.0)
            iv_bonus_base += p2.shop_flags["bad_gender_fix_m"].get("iv_penalty", 0.0)

        if "bad_gender_fix_f" in p1.shop_flags:
            gender_bias_f_chance = p1.shop_flags["bad_gender_fix_f"].get("chance", 0.0)
            iv_bonus_base += p1.shop_flags["bad_gender_fix_f"].get("iv_penalty", 0.0)
        if "bad_gender_fix_f" in p2.shop_flags:
            gender_bias_f_chance = p2.shop_flags["bad_gender_fix_f"].get("chance", 0.0)
            iv_bonus_base += p2.shop_flags["bad_gender_fix_f"].get("iv_penalty", 0.0)

        return {
            "iv_bonus_base": iv_bonus_base,
            "high_iv_bonus": high_iv_bonus,
            "mutation_chance_delta": mutation_chance_delta,
            "taboo_depth_add": taboo_depth_add,
            "gender_bias_m_chance": gender_bias_m_chance,
            "gender_bias_f_chance": gender_bias_f_chance,
        }

    @staticmethod
    def get_training_modifiers(dobu: Dobumon) -> Dict[str, Any]:
        """
        ショップフラグからトレーニング時の上昇量補正や特殊フラグを計算します。
        """
        multiplier = 1.0
        if "suicidal_drug" in dobu.shop_flags:
            multiplier *= dobu.shop_flags["suicidal_drug"].get("train_mult", 1.0)
        if "muscle_booster" in dobu.shop_flags:
            multiplier *= dobu.shop_flags["muscle_booster"].get("mult", 1.0)

        ignore_diminishing_returns = "cooling_sheet" in dobu.shop_flags

        return {
            "multiplier": multiplier,
            "ignore_diminishing_returns": ignore_diminishing_returns,
        }

    @staticmethod
    def get_combat_modifiers(dobu: Dobumon) -> Dict[str, float]:
        """
        ショップフラグから戦闘時のステータス補正倍率を計算します。
        """
        # 忌血の触媒 (全能力+20%)
        stat_multiplier = 1.2 if "blood_catalyst" in dobu.shop_flags else 1.0

        return {
            "atk": stat_multiplier,
            "defense": stat_multiplier,
            "spd": stat_multiplier,
            "eva": stat_multiplier,
        }
