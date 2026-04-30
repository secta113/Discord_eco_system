from typing import Dict

from logic.dobumon.core.dob_exceptions import DobumonNotFoundError
from logic.dobumon.dob_battle.dob_settlement import BattleSettlementManager


class BattleHandler:
    """
    怒武者の対人戦（PvP）決済を担当するハンドラー。
    """

    def __init__(self, manager):
        self.manager = manager

    def settle_battle(self, winner_id: str, loser_id: str, battle_result: Dict = None) -> Dict:
        """
        戦闘結果をシステムに反映させます。
        """
        winner = self.manager.get_dobumon(winner_id)
        loser = self.manager.get_dobumon(loser_id)

        if not winner or not loser:
            raise DobumonNotFoundError("バトルの決済対象となる個体が見つかりません。")

        settlement = BattleSettlementManager.settle_pvp(winner, loser, battle_result)

        # 敗北者の死亡処理を集約
        self.manager.handle_death(loser, "Defeated in PvP Battle")

        # 忌血の触媒の消費
        for d in [winner, loser]:
            if "blood_catalyst" in d.shop_flags:
                del d.shop_flags["blood_catalyst"]

        # 永続化
        self.manager.save_dobumon(winner)
        self.manager.save_dobumon(loser)

        return settlement
