from typing import List, Tuple

from .bj_deck import Deck


class BlackjackHand:
    """単一の手札の状態とロジックを管理"""

    def __init__(self, cards: List[Tuple[str, str]] = None, bet: int = 0):
        self.cards = cards or []
        self.bet = bet
        self.status = "playing"  # playing | stand | bust | blackjack
        self.is_doubled = False
        self.hospitality_triggered = False

    @property
    def score(self) -> int:
        return Deck.get_score(self.cards)

    @property
    def is_bj(self) -> bool:
        return self.score == 21 and len(self.cards) == 2

    def add_card(self, card: Tuple[str, str]):
        self.cards.append(card)
        if self.score > 21:
            self.status = "bust"
        elif len(self.cards) == 6 and self.score <= 21:
            # 6-Card Charlie 強制スタンド
            self.status = "stand"

    def to_dict(self):
        return {
            "hand": self.cards,
            "status": self.status,
            "bet": self.bet,
            "is_doubled": self.is_doubled,
            "hospitality_triggered": self.hospitality_triggered,
        }

    @classmethod
    def from_dict(cls, data):
        obj = cls(data["hand"], data["bet"])
        obj.status = data["status"]
        obj.is_doubled = data.get("is_doubled", False)
        obj.hospitality_triggered = data.get("hospitality_triggered", False)
        return obj

    def get_rare_hand_info(self) -> dict:
        """特殊役の判定ロジック"""
        score = self.score
        ranks = [c[1] for c in self.cards]

        is_777 = len(self.cards) == 3 and all(r == "7" for r in ranks)
        is_678 = False
        if len(self.cards) == 3:
            # J,Q,Kは10として扱う
            val_ranks = sorted([Deck.VALUES[r] if r not in ["J", "Q", "K"] else 10 for r in ranks])
            if val_ranks == [6, 7, 8]:
                is_678 = True

        is_6charlie = len(self.cards) == 6 and score <= 21

        is_suited_bj = False
        if self.status == "blackjack" and len(self.cards) == 2:
            if self.cards[0][0] == self.cards[1][0]:
                is_suited_bj = True

        return {
            "is_777": is_777,
            "is_678": is_678,
            "is_6charlie": is_6charlie,
            "is_suited_bj": is_suited_bj,
            "has_any": is_777 or is_678 or is_6charlie or is_suited_bj,
        }


class BlackjackPlayer:
    """ユーザー1人の状態（複数手札）を管理"""

    def __init__(self, user_id: int, asset_rank: str = "Standard"):
        self.user_id = user_id
        self.asset_rank = asset_rank
        self.hands: List[BlackjackHand] = []
        self.active_hand_index = 0

    def add_hand(self, hand: BlackjackHand):
        self.hands.append(hand)

    def get_active_hand(self) -> BlackjackHand:
        if 0 <= self.active_hand_index < len(self.hands):
            return self.hands[self.active_hand_index]
        return None

    def to_dict(self):
        return {
            "hands": [h.to_dict() for h in self.hands],
            "active_hand_index": self.active_hand_index,
            "asset_rank": self.asset_rank,
        }

    @classmethod
    def from_dict(cls, user_id: int, data: dict):
        obj = cls(user_id, asset_rank=data.get("asset_rank", "Standard"))
        obj.hands = [BlackjackHand.from_dict(h) for h in data["hands"]]
        obj.active_hand_index = data.get("active_hand_index", 0)
        return obj
