import random
from typing import Dict, Optional

from logic.dobumon.core.dob_exceptions import DobumonNotFoundError
from logic.dobumon.core.dob_factory import DobumonFactory
from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.dob_battle.wild.wild_config import WildBattleConfig
from logic.dobumon.dob_battle.wild.wild_settlement import WildSettlementManager


class WildHandler:
    """
    野生の怒武者生成と野生戦の決済を担当するハンドラー。
    """

    def __init__(self, manager):
        self.manager = manager

    def create_wild_dobumon(self, _player_dobu: Dobumon, rank_key: str = "C") -> Dobumon:
        """
        野生の怒武者を生成します。
        """
        rank_info = WildBattleConfig.get_rank(rank_key)
        if not rank_info:
            rank_info = WildBattleConfig.get_rank("C")

        map_info = random.choice(rank_info["maps"])

        return DobumonFactory.create_wild(
            stats_config=rank_info["stats"],
            attribute=map_info["attribute"],
            forbidden_depth=rank_info.get("forbidden_depth", 0),
        )

    def settle_wild_battle(
        self,
        winner_id: str,
        player_dobu_id: str,
        wild_dobu: Dobumon,
        rank_key: str = "C",
        battle_result: Dict = None,
    ) -> Dict:
        """
        野生戦の結果を決済します。
        """
        player_dobu = self.manager.get_dobumon(player_dobu_id)
        if not player_dobu:
            raise DobumonNotFoundError("野生戦の決済対象となる自分の個体が見つかりません。")

        # 単体テスト等で wild_dobu がオブジェクトではなく dict で渡されるケースへの対応
        if isinstance(wild_dobu, dict):
            rank_info = WildBattleConfig.get_rank(rank_key)
            dummy_wild = DobumonFactory.create_wild(
                stats_config=rank_info["stats"],
                attribute=random.choice(rank_info["maps"])["attribute"],
            )
            dummy_wild.name = "野生のドブ"
            wild_dobu = dummy_wild

        settlement = WildSettlementManager.calculate_settlement(
            player_dobu, wild_dobu, winner_id, rank_key, battle_result
        )

        if settlement["winner"] != "player":
            self.manager.handle_death(player_dobu, "Defeated in Wild Battle")
        else:
            # 勝利時の成長適用
            gains = settlement.get("gains")
            if gains:
                from logic.dobumon.training import WildGrowthEngine

                WildGrowthEngine.apply_gains(player_dobu, gains)

        # 忌血の触媒の消費
        if "blood_catalyst" in player_dobu.shop_flags:
            del player_dobu.shop_flags["blood_catalyst"]

        self.manager.save_dobumon(player_dobu)
        return settlement
