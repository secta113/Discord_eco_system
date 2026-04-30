from typing import Dict, Optional

from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.dob_battle.dob_settlement import BattleSettlementManager

from .wild_config import WildBattleConfig


class WildSettlementManager:
    """
    野生戦特有の精算ロジック（報酬倍率、属性不利ボーナス）を管理します。
    """

    @staticmethod
    def calculate_settlement(
        player_dobu: Dobumon,
        wild_dobu: Dobumon,
        winner_id: str,
        rank_key: str,
        battle_result: Optional[Dict] = None,
    ) -> Dict:
        # コア精算の実行
        settlement = BattleSettlementManager.settle_wild(
            player_dobu, wild_dobu.name, winner_id, battle_result
        )

        if settlement["winner"] == "player":
            rank_info = WildBattleConfig.get_rank(rank_key)
            if not rank_info:
                return settlement

            # 1. ランクに応じた基本報酬の上書き
            base_reward = rank_info["reward_base"]

            # 2. 属性不利ボーナスの計算
            is_disadvantage = WildSettlementManager._check_attribute_disadvantage(
                player_dobu.attribute, wild_dobu.attribute
            )

            bonus_mult = 1.0
            if is_disadvantage:
                bonus_mult += WildBattleConfig.get_disadvantage_bonus()

            final_reward = int(base_reward * bonus_mult)

            # 特性補正（本来は settle_wild 内で行われているが、報酬を上書きするため再計算が必要な場合がある）
            # ここでは単純にランクベースの報酬を最終値として settlement にセットする
            settlement["reward"] = final_reward
            settlement["is_disadvantage_bonus"] = is_disadvantage

            # 経験値（gains）への反映
            if "gains" in settlement:
                exp_mult = rank_info["exp_mult"] * bonus_mult
                for stat in settlement["gains"]:
                    settlement["gains"][stat] = round(settlement["gains"][stat] * exp_mult, 2)

        return settlement

    @staticmethod
    def _check_attribute_disadvantage(player_attr: str, wild_attr: str) -> bool:
        """
        プレイヤーが属性的に不利な状況（被ダメージ増、与ダメージ減）にあるか判定。
        fire > grass > water > fire
        """
        disadvantage_map = {"fire": "water", "water": "grass", "grass": "fire"}
        return disadvantage_map.get(player_attr) == wild_attr
