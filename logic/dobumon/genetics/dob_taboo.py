from typing import TYPE_CHECKING, Any, Dict, List, Tuple

if TYPE_CHECKING:
    from logic.dobumon.core.dob_models import Dobumon


class TabooLogic:
    """
    禁忌深度、背反、禁断に関わる特殊な計算ロジックを一元管理するクラス。
    """

    @staticmethod
    def calculate_child_forbidden_depth(
        p1_depth: int, p2_depth: int, is_taboo_breeding: bool, is_forbidden_trigger: bool
    ) -> int:
        """
        子の禁忌深度を計算します。
        禁断発生時は加算(sum)＋ボーナス(+2)、それ以外は最大値(max)をベースにします。
        """
        bonus = 1 if is_taboo_breeding else 0

        if is_forbidden_trigger:
            # 禁断発現時は両親の合計に加えて、覚醒ボーナス(+2)を付与
            return p1_depth + p2_depth + bonus + 2
        else:
            return max(p1_depth, p2_depth) + bonus

    @staticmethod
    def resolve_taboo_transformation(
        current_traits: List[str], genetics_meta: Dict[str, Any], gender: str
    ) -> Tuple[List[str], bool, Dict[str, Any]]:
        """
        特性の変異（対禁忌->背反、背反+禁忌->禁断）を解決し、性別による因子のフィルタリングを行います。
        """
        new_traits = list(current_traits)
        new_meta = dict(genetics_meta)
        is_forbidden_output = False

        has_red = new_meta.get("has_forbidden_red", False)
        has_blue = new_meta.get("has_forbidden_blue", False)

        # 1. 背反 (antinomy) の解決: 対禁忌アレルがあり、かつ禁忌因子（赤または青）を保持している場合
        if "anti_taboo" in new_traits and (has_red or has_blue):
            new_traits.remove("anti_taboo")
            if "antinomy" not in new_traits:
                new_traits.append("antinomy")

        # 2. 禁断 (the_forbidden) の解決: 背反の状態で、かつ赤と青の両方の因子が揃った場合
        if "antinomy" in new_traits and has_red and has_blue:
            if "the_forbidden" not in new_traits:
                new_traits.append("the_forbidden")
                is_forbidden_output = True
            if "antinomy" in new_traits:
                new_traits.remove("antinomy")

        # 3. 性別による因子と特性の制限 (性別ロックと昇華)
        if "antinomy" in new_traits or "the_forbidden" in new_traits:
            # 背反または禁断個体は「昇華」しており、性別に関わらず両方の特性を発現できる
            if has_red and "forbidden_red" not in new_traits:
                new_traits.append("forbidden_red")
            if has_blue and "forbidden_blue" not in new_traits:
                new_traits.append("forbidden_blue")
        else:
            # 通常個体は、性別に合わない因子を保持できず、特性も除去される
            if gender == "M":
                if "has_forbidden_blue" in new_meta:
                    del new_meta["has_forbidden_blue"]
                if "forbidden_blue" in new_traits:
                    new_traits.remove("forbidden_blue")
            elif gender == "F":
                if "has_forbidden_red" in new_meta:
                    del new_meta["has_forbidden_red"]
                if "forbidden_red" in new_traits:
                    new_traits.remove("forbidden_red")

        return new_traits, is_forbidden_output, new_meta

    @staticmethod
    def apply_status_modifiers(dobumon: "Dobumon", base_mod: float) -> float:
        """
        寿命消費率（consumption_mod）に対する禁忌の影響を計算します。
        """
        depth = dobumon.genetics.get("forbidden_depth", 0)
        traits = dobumon.traits

        if "antinomy" in traits or "the_forbidden" in traits:
            return base_mod

        if depth > 0:
            return base_mod * (1.2**depth)

        return base_mod

    @staticmethod
    def get_growth_multiplier(dobumon: "Dobumon", base_multiplier: float) -> float:
        """
        成長倍率に対する禁忌の影響を計算します。
        """
        traits = dobumon.traits
        depth = dobumon.genetics.get("forbidden_depth", 0)

        if "the_forbidden" in traits:
            return base_multiplier * (max(1, depth) / 0.7)

        return base_multiplier

    @staticmethod
    def get_combat_modifiers(subject: "Dobumon", opponent: "Dobumon") -> Dict[str, float]:
        """
        自身(subject)が相手(opponent)と対峙した際に得るステータス補正を計算します。
        """
        mods = {"atk": 1.0, "defense": 1.0, "hp": 1.0, "eva": 1.0, "spd": 1.0}

        if "anti_taboo" in subject.traits:
            if "the_forbidden" in opponent.traits:
                for key in mods:
                    mods[key] *= 10.0
                return mods

            target_depth = opponent.genetics.get("forbidden_depth", 0)
            if target_depth > 0:
                bonus = 1.0 + (target_depth * 0.3)
                mods["atk"] *= bonus
                mods["defense"] *= bonus

        return mods
