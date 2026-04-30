import random


class PokerDeck:
    """ポーカー用52枚デッキ"""

    SUITS = ["♠", "♣", "♥", "♦"]
    RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
    # 役判定用の数値変換 (2=2, ..., 10=10, J=11, Q=12, K=13, A=14)
    RANK_MAP = {
        "2": 2,
        "3": 3,
        "4": 4,
        "5": 5,
        "6": 6,
        "7": 7,
        "8": 8,
        "9": 9,
        "10": 10,
        "J": 11,
        "Q": 12,
        "K": 13,
        "A": 14,
    }

    SUIT_EMOJI = {
        "♠": "♠️",
        "♥": "♥️",
        "♦": "♦️",
        "♣": "♣️",
    }

    PLACEHOLDER_CARD = "⬜"

    def __init__(self):
        self.cards = [(s, r) for s in self.SUITS for r in self.RANKS]
        self.shuffle()

    def shuffle(self):
        random.shuffle(self.cards)

    def draw(self):
        if not self.cards:
            return None
        return self.cards.pop()

    @staticmethod
    def format_card(card):
        """カードを絵文字形式でフォーマット (例: ♠️A, ♥️10)"""
        if not card:
            return PokerDeck.PLACEHOLDER_CARD
        suit_emoji = PokerDeck.SUIT_EMOJI.get(card[0], card[0])
        return f"{suit_emoji}{card[1]}"

    @staticmethod
    def format_card_ansi(card):
        """DEPRECATED: 互換性のために維持。現在は format_card と同じ挙動"""
        return PokerDeck.format_card(card)
