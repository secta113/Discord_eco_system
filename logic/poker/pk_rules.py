from collections import Counter
from typing import List, Tuple

from .pk_deck import PokerDeck


class PokerRules:
    """テキサス・ホールデムの役判定ロジック"""

    HAND_RANK_ROYAL_FLUSH = 10
    HAND_RANK_STRAIGHT_FLUSH = 9
    HAND_RANK_FOUR_OF_A_KIND = 8
    HAND_RANK_FULL_HOUSE = 7
    HAND_RANK_FLUSH = 6
    HAND_RANK_STRAIGHT = 5
    HAND_RANK_THREE_OF_A_KIND = 4
    HAND_RANK_TWO_PAIR = 3
    HAND_RANK_ONE_PAIR = 2
    HAND_RANK_HIGH_CARD = 1

    HAND_NAMES = {
        10: "ロイヤルフラッシュ",
        9: "ストレートフラッシュ",
        8: "フォー・オブ・ア・カインド",
        7: "フルハウス",
        6: "フラッシュ",
        5: "ストレート",
        4: "スリー・オブ・ア・カインド",
        3: "ツーペア",
        2: "ワンペア",
        1: "ハイカード",
    }

    @staticmethod
    def get_best_hand(cards: List[Tuple[str, str]]) -> Tuple[int, List[int], str]:
        """
        7枚のカードから最強の5枚の役を判定。
        戻り値: (役ランク, キッカー等を含む強さ比較用リスト, 役名)
        """
        from itertools import combinations

        if len(cards) < 5:
            # 暫定的に全カードを評価対象とする
            rank, strength = PokerRules.evaluate_5_cards(cards)
            return rank, strength, PokerRules.HAND_NAMES.get(rank, "未知")

        best_rank = -1
        best_strength = []

        # 7枚から5枚選ぶ全組み合わせ (21通り) をチェック
        for combo in combinations(cards, 5):
            rank, strength = PokerRules.evaluate_5_cards(list(combo))
            if rank > best_rank:
                best_rank = rank
                best_strength = strength
            elif rank == best_rank:
                if strength > best_strength:
                    best_strength = strength

        return best_rank, best_strength, PokerRules.HAND_NAMES[best_rank]

    @staticmethod
    def get_best_hand_provisional(cards: List[Tuple[str, str]]) -> Tuple[int, List[int], str]:
        """
        5枚未満のカードから暫定的な役を判定。
        戻り値: (暫定ランク, 強さ比較用リスト, 役名)
        """
        ranks = sorted([PokerDeck.RANK_MAP[c[1]] for c in cards], reverse=True)
        counts = Counter(ranks)
        count_values = sorted(counts.values(), reverse=True)
        rank_by_count = sorted(counts.keys(), key=lambda r: (counts[r], r), reverse=True)

        if count_values == [4]:
            return PokerRules.HAND_RANK_FOUR_OF_A_KIND, rank_by_count, "フォー・オブ・ア・カインド"
        if count_values == [3]:
            return PokerRules.HAND_RANK_THREE_OF_A_KIND, rank_by_count, "スリー・オブ・ア・カインド"
        if count_values == [2, 2]:
            return PokerRules.HAND_RANK_TWO_PAIR, rank_by_count, "ツーペア"
        if count_values == [2]:
            return PokerRules.HAND_RANK_ONE_PAIR, rank_by_count, "ワンペア"

        return PokerRules.HAND_RANK_HIGH_CARD, ranks, "ハイカード"

    @staticmethod
    def get_outs_count(cards: List[Tuple[str, str]]) -> int:
        """
        ストレートやフラッシュを完成させるために必要な残りカード枚数（アウツ）を概算。
        """
        if len(cards) < 4:
            return 0

        suits = [c[0] for c in cards]
        ranks = sorted({PokerDeck.RANK_MAP[c[1]] for c in cards})

        outs = 0
        # フラッシュドローのチェック (4枚同スート)
        suit_counts = Counter(suits)
        if any(v == 4 for v in suit_counts.values()):
            outs += 9  # 同スート残り9枚

        # ストレートドローのチェック (4枚連続)
        # A, 2, 3, 4, 5 特殊対応
        if 14 in ranks:
            ranks_with_ace_low = sorted(ranks + [1])
        else:
            ranks_with_ace_low = ranks

        for i in range(len(ranks_with_ace_low) - 3):
            sub = ranks_with_ace_low[i : i + 4]
            if max(sub) - min(sub) <= 4:
                # 穴あきドロー(ガンショット)の場合は4枚、両面なら8枚だが簡略化して4~8枚
                if max(sub) - min(sub) == 3:
                    outs += 4  # 両面または片面
                else:
                    outs += 2  # ガンショット

        return min(outs, 15)  # 最大値を制限

    @staticmethod
    def evaluate_5_cards(cards: List[Tuple[str, str]]) -> Tuple[int, List[int]]:
        """5枚のカードの役を判定"""
        suits = [c[0] for c in cards]
        ranks = sorted([PokerDeck.RANK_MAP[c[1]] for c in cards], reverse=True)

        counts = Counter(ranks)
        count_values = sorted(counts.values(), reverse=True)
        rank_by_count = sorted(counts.keys(), key=lambda r: (counts[r], r), reverse=True)

        is_flush = len(set(suits)) == 1

        # ストレート判定 (A-2-3-4-5 特殊対応)
        is_straight = False
        if len(set(ranks)) == 5 and (max(ranks) - min(ranks) == 4):
            is_straight = True
        elif set(ranks) == {14, 2, 3, 4, 5}:  # A-2-3-4-5
            is_straight = True
            ranks = [5, 4, 3, 2, 1]  # 強さ比較用に 14(A) を 1 に変換

        # 役判定 (高い方から)
        if is_flush and is_straight:
            if max(ranks) == 14:
                return PokerRules.HAND_RANK_ROYAL_FLUSH, [14]
            return PokerRules.HAND_RANK_STRAIGHT_FLUSH, [max(ranks)]

        if count_values == [4, 1]:
            return PokerRules.HAND_RANK_FOUR_OF_A_KIND, rank_by_count

        if count_values == [3, 2]:
            return PokerRules.HAND_RANK_FULL_HOUSE, rank_by_count

        if is_flush:
            return PokerRules.HAND_RANK_FLUSH, ranks

        if is_straight:
            return PokerRules.HAND_RANK_STRAIGHT, [max(ranks)]

        if count_values == [3, 1, 1]:
            return PokerRules.HAND_RANK_THREE_OF_A_KIND, rank_by_count

        if count_values == [2, 2, 1]:
            return PokerRules.HAND_RANK_TWO_PAIR, rank_by_count

        if count_values == [2, 1, 1, 1]:
            return PokerRules.HAND_RANK_ONE_PAIR, rank_by_count

        return PokerRules.HAND_RANK_HIGH_CARD, ranks
