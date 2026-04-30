from typing import List, Optional


class PokerPlayer:
    """テキサス・ホールデムのプレイヤー状態"""

    def __init__(
        self,
        user_id: int,
        name: str,
        stack: int = 0,
        is_npc: bool = False,
        ai_rank: Optional[str] = None,
        personality: Optional[str] = None,
        risk_level: float = 0.5,
        asset_rank: str = "Standard",
    ):
        self.user_id = user_id
        self.name = name
        self.stack = stack  # テーブル上の持ち点（チップ）
        self.is_npc = is_npc
        self.ai_rank = ai_rank
        self.personality = personality
        self.risk_level = risk_level
        self.asset_rank = asset_rank
        self.hole_cards = []
        self.status = "playing"  # playing, folded, all_in
        self.current_bet = 0  # 現在のラウンドでのベット額
        self.total_bet = 0  # ゲーム全体での累計ベット額
        self.is_turn_done = False  # このラウンドでアクション済みか
        self.final_hand_name: Optional[str] = None
        self.final_rank: Optional[int] = None

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "name": self.name,
            "stack": self.stack,
            "is_npc": self.is_npc,
            "ai_rank": self.ai_rank,
            "personality": self.personality,
            "risk_level": self.risk_level,
            "asset_rank": self.asset_rank,
            "hole_cards": self.hole_cards,
            "status": self.status,
            "current_bet": self.current_bet,
            "total_bet": self.total_bet,
            "is_turn_done": self.is_turn_done,
            "final_hand_name": self.final_hand_name,
            "final_rank": self.final_rank,
        }

    @classmethod
    def from_dict(cls, data):
        obj = cls(
            data["user_id"],
            data["name"],
            data.get("stack", 0),
            is_npc=data.get("is_npc", False),
            ai_rank=data.get("ai_rank"),
            personality=data.get("personality"),
            risk_level=data.get("risk_level", 0.5),
            asset_rank=data.get("asset_rank", "Standard"),
        )
        obj.hole_cards = data.get("hole_cards", [])
        obj.status = data.get("status", "playing")
        obj.current_bet = data.get("current_bet", 0)
        obj.total_bet = data.get("total_bet", 0)
        obj.is_turn_done = data.get("is_turn_done", False)
        obj.final_hand_name = data.get("final_hand_name")
        obj.final_rank = data.get("final_rank")
        return obj

    @property
    def is_all_in(self) -> bool:
        return self.status == "all_in" or self.stack == 0

    def reset_round_bet(self):
        self.current_bet = 0
        self.is_turn_done = False

    def fold(self):
        self.status = "folded"
        self.is_turn_done = True
