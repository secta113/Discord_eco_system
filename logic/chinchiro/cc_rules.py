from typing import Dict, List, Tuple


class ChinchiroRules:
    """役判定、勝利判定、配当ルールを管理"""

    @staticmethod
    def calculate_role(dice: List[int]) -> Tuple[str, int]:
        """ダイスの目から役名と強さを判定"""
        d = sorted(dice)
        if d == [1, 1, 1]:
            return "ピンゾロ", 5000
        if d[0] == d[1] == d[2]:
            return f"{d[0]}のアラシ", 2000 + d[0]
        if d == [4, 5, 6]:
            return "シゴロ", 1000
        if d == [1, 2, 3]:
            return "ヒフミ", -1000

        p = d[2] if d[0] == d[1] else d[0] if d[1] == d[2] else d[1] if d[0] == d[2] else None
        if p:
            return f"{p}の目", 100 + p
        return "目なし", 0

    @staticmethod
    def determine_winner(scores: List[dict]) -> dict:
        """強さ順でソートし、勝者を決定"""
        if not scores:
            return None
        sorted_scores = sorted(scores, key=lambda x: x["strength"], reverse=True)
        return sorted_scores[0]

    @staticmethod
    def get_settlement_breakdown(pot: int, is_pvp: bool, is_oya_winner: bool) -> Tuple[int, int]:
        """(勝者への配当額, システム徴収額) の内訳を計算"""
        tax = 0
        if is_pvp and is_oya_winner:
            tax = int(pot * 0.05)
        return pot - tax, tax
