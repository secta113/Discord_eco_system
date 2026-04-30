from typing import List, Optional


class ChinchiroHand:
    """単一のロール（3ダイス）とその状態を管理"""

    def __init__(self, dice: List[int] = None, roll_count: int = 0):
        self.dice = dice or []
        self.roll_count = roll_count
        self.strength = 0
        self.role_name = "目なし"
        self.is_fixed = False
        self.hospitality_triggered = False

    def to_dict(self):
        return {
            "dice": self.dice,
            "roll_count": self.roll_count,
            "strength": self.strength,
            "role_name": self.role_name,
            "is_fixed": self.is_fixed,
            "hospitality_triggered": self.hospitality_triggered,
        }

    @classmethod
    def from_dict(cls, data):
        obj = cls(data.get("dice"), data.get("roll_count", 0))
        obj.strength = data.get("strength", 0)
        obj.role_name = data.get("role_name", "目なし")
        obj.is_fixed = data.get("is_fixed", False)
        obj.hospitality_triggered = data.get("hospitality_triggered", False)
        return obj


class ChinchiroPlayer:
    """ユーザー1人の状態を管理"""

    def __init__(self, user_id: int, asset_rank: str = "Standard"):
        self.user_id = user_id
        self.asset_rank = asset_rank
        self.hand: Optional[ChinchiroHand] = None

    def set_hand(self, hand: ChinchiroHand):
        self.hand = hand

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "asset_rank": self.asset_rank,
            "hand": self.hand.to_dict() if self.hand else None,
        }

    @classmethod
    def from_dict(cls, data):
        obj = cls(data["user_id"], asset_rank=data.get("asset_rank", "Standard"))
        if data.get("hand"):
            obj.hand = ChinchiroHand.from_dict(data["hand"])
        return obj
