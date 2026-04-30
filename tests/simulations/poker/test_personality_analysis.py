import os
import random
import sys
from collections import Counter
from typing import Dict, List, Tuple
from unittest.mock import MagicMock

# プロジェクトルートをパスに追加 (3段階遡る)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from logic.poker.ai.personality import apply_personality
from logic.poker.pk_models import PokerPlayer


def run_scenario(
    personality: str,
    risk_level: float,
    base_action: str,
    needed_to_call: int,
    table_avg_stack: int,
    trials: int = 1000,
) -> Dict[str, float]:
    """特定のシチュエーションでアクションを試行し、統計を返す"""
    session = MagicMock()
    session.current_max_bet = needed_to_call
    session.big_blind = 100
    session.table_average_stack = table_avg_stack

    player = PokerPlayer(1, "TestBot", personality=personality, risk_level=risk_level, stack=10000)
    player.current_bet = 0

    actions = Counter()
    for _ in range(trials):
        # apply_personality の内部で乱数を使用するため、複数回試行して確率分布を得る
        res_action, _ = apply_personality(base_action, 0, session, player)
        actions[res_action] += 1

    stats = {action: (count / trials) * 100 for action, count in actions.items()}
    return stats


def print_report():
    print("# ポーカーAI性格・リスク行動分析レポート\n")

    personalities = ["aggressive", "timid", "calculated", "normal", "bluffer", "station", "shark"]
    risks = [0.1, 0.5, 0.9]

    # --- シナリオ1: プレッシャーのかかる場面 (Needed = 1/2 of average stack) ---
    print("## シナリオ1: 強いプレッシャー (中程度の投入が必要な場面)")
    print("条件: needed_to_call=1000, table_avg=2000 (Weight=0.5)\n")
    print("| 性格 | リスク | FOLD% | CALL% | RAISE% |")
    print("| :--- | :--- | :---: | :---: | :---: |")

    for ptype in personalities:
        for risk in risks:
            stats = run_scenario(ptype, risk, "call", 1000, 2000)
            print(
                f"| {ptype:10} | {risk:.1f} | {stats.get('fold', 0):5.1f}% | {stats.get('call', 0):5.1f}% | {stats.get('raise', 0):5.1f}% |"
            )
    print("\n")

    # --- シナリオ2: 0ポイント・チェック可能な場面 ---
    print("## シナリオ2: 無料の局面 (チェック可能)")
    print("条件: needed_to_call=0, table_avg=2000 (Weight=0.0)\n")
    print("| 性格 | リスク | FOLD% | CHECK% | RAISE% |")
    print("| :--- | :--- | :---: | :---: | :---: |")

    for ptype in personalities:
        for risk in risks:
            stats = run_scenario(ptype, risk, "check", 0, 2000)
            # needed_to_call=0 ならフォールドは 0% であるべき
            print(
                f"| {ptype:10} | {risk:.1f} | {stats.get('fold', 0):5.1f}% | {stats.get('check', 0):5.1f}% | {stats.get('raise', 0):5.1f}% |"
            )
    print("\n")

    # --- シナリオ3: ブラフのチャンス (手札に自信がない想定でのcheckアクション) ---
    print("## シナリオ3: ブラフ判定 (ブラフ性格の挙動)")
    print("条件: needed_to_call=0, 手札ランクに関わらず性格が介入する場合\n")
    print("| 性格 | リスク | RAISE(BLUFF)% | 備考 |")
    print("| :--- | :--- | :---: | :--- |")

    for ptype in ["bluffer", "aggressive", "normal"]:
        for risk in [0.9]:  # 高リスク設定
            stats = run_scenario(ptype, risk, "check", 0, 2000)
            print(
                f"| {ptype:10} | {risk:.1f} | {stats.get('raise', 0):5.1f}% | Risk 0.9 での強気度 |"
            )


if __name__ == "__main__":
    print_report()
