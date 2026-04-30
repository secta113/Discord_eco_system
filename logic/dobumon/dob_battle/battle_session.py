from typing import Dict, List, Optional

from managers.game_session import BaseGameSession


class DobumonBattleSession(BaseGameSession):
    """
    ドブモン戦闘（PvP/野生戦）のセッション管理クラス。
    """

    def __init__(self, channel_id: int):
        # ドブモン戦闘は原則無料（トレーニング等とは別）なので bet_amount=0
        super().__init__(channel_id, bet_amount=0)
        self.attacker_data: Dict = {}
        self.defender_data: Dict = {}
        self.steps: List[Dict] = []
        self.winner_id: Optional[str] = None
        self.loser_id: Optional[str] = None
        self.battle_type: str = "challenge"  # challenge | wild

    @property
    def game_type(self) -> str:
        return "dobumon_battle"

    @property
    def game_name(self) -> str:
        return "怒武者決闘"

    def to_dict(self) -> Dict:
        data = super().to_dict()
        data.update(
            {
                "attacker_data": self.attacker_data,
                "defender_data": self.defender_data,
                "steps": self.steps,
                "winner_id": self.winner_id,
                "loser_id": self.loser_id,
                "battle_type": self.battle_type,
            }
        )
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "DobumonBattleSession":
        obj = cls(data["channel_id"])
        # BaseGameSession の from_dict と同様の初期化
        obj.status = data["status"]
        obj.players = data["players"]

        # 個別データの復元
        obj.attacker_data = data.get("attacker_data", {})
        obj.defender_data = data.get("defender_data", {})
        obj.steps = data.get("steps", [])
        obj.winner_id = data.get("winner_id")
        obj.loser_id = data.get("loser_id")
        obj.battle_type = data.get("battle_type", "challenge")
        return obj
