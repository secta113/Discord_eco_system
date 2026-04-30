import random


class Deck:
    """汎用カードデッキ"""

    SUITS = ["♠", "♣", "♥", "♦"]
    RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
    VALUES = {
        "A": 1,
        "2": 2,
        "3": 3,
        "4": 4,
        "5": 5,
        "6": 6,
        "7": 7,
        "8": 8,
        "9": 9,
        "10": 10,
        "J": 10,
        "Q": 10,
        "K": 10,
    }

    def __init__(self):
        self.cards = [(s, r) for s in self.SUITS for r in self.RANKS] * 8
        random.shuffle(self.cards)

    def draw(self):
        return self.cards.pop()

    def peek(self):
        return self.cards[-1] if self.cards else None

    def move_top_to_bottom(self):
        if len(self.cards) > 1:
            card = self.cards.pop()
            self.cards.insert(0, card)

    def swap_top_with_ten(self):
        """デッキ内の一番近い10点カードをトップと入れ替える（接待用）"""
        for i in range(len(self.cards) - 1, -1, -1):
            if Deck.VALUES[self.cards[i][1]] == 10:
                self.cards[i], self.cards[-1] = self.cards[-1], self.cards[i]
                return True
        return False

    @staticmethod
    def format_card(card):
        return f"{card[0]}{card[1]}"

    @staticmethod
    def get_score(hand):
        score = sum(Deck.VALUES[c[1]] for c in hand)
        aces = sum(1 for c in hand if c[1] == "A")
        while score <= 11 and aces > 0:
            score += 10
            aces -= 1
        return score
