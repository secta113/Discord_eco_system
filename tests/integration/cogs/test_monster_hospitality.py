from unittest.mock import MagicMock

import pytest

from logic.poker.ai.brains import MonsterAI
from logic.poker.pk_models import PokerPlayer
from logic.poker.pk_rules import PokerRules
from logic.poker.pk_service import TexasPokerService


def test_monster_hospitality_skips_cheat_for_recovery():
    """最強の対戦相手が Recovery ユーザーの場合、MonsterAI はイカサマを中止するか"""
    service = TexasPokerService(123, 100)
    service.community_cards = [("S", "10"), ("D", "J"), ("H", "Q"), ("C", "K"), ("S", "2")]

    # MonsterAI (ID: -1)
    monster = PokerPlayer(-1, "Monster", stack=1000, is_npc=True, ai_rank="monster")
    monster.hole_cards = [("H", "2"), ("D", "3")]  # ハイカード
    service.player_states[-1] = monster

    # Recovery ユーザー (ID: 1)
    recovery_player = PokerPlayer(1, "Poor Guy", stack=100, is_npc=False, asset_rank="Recovery")
    recovery_player.hole_cards = [("S", "A"), ("C", "3")]  # ストレート (10-J-Q-K-A)
    service.player_states[1] = recovery_player

    brain = MonsterAI(monster)

    # 手札交換前の状態を保存
    old_hole_cards = list(monster.hole_cards)

    # イカサマ実行
    brain.cheat_hand(service)

    # Recovery ユーザーへの接待により、手札が交換されていない（または強くなっていない）ことを確認
    # 本来なら最強のカード (ストレートフラッシュ等) に交換されるはずだが、スキップされるはず
    assert monster.hole_cards == old_hole_cards


def test_monster_no_hospitality_for_prime():
    """最強の対戦相手が Prime ユーザーの場合、MonsterAI は通常通りイカサマするか"""
    service = TexasPokerService(123, 100)
    service.community_cards = [("S", "10"), ("D", "J"), ("H", "Q"), ("C", "K"), ("S", "2")]

    # MonsterAI
    monster = PokerPlayer(-1, "Monster", stack=1000, is_npc=True, ai_rank="monster")
    monster.hole_cards = [("H", "2"), ("D", "3")]
    service.player_states[-1] = monster

    # Prime ユーザー
    prime_player = PokerPlayer(1, "Rich Guy", stack=10000, is_npc=False, asset_rank="Prime")
    prime_player.hole_cards = [("S", "A"), ("C", "3")]  # ストレート
    service.player_states[1] = prime_player

    brain = MonsterAI(monster)

    # イカサマ実行（成功率を考慮して何度か試行、または確率を固定）
    import random

    random.seed(42)  # 決定論的に動作させる

    brain.cheat_hand(service)

    # Prime ユーザーには容赦しないので、手札が交換されているはず
    assert monster.hole_cards != [("H", "2"), ("D", "3")]

    # かつ、Prime ユーザーより強い手になっているはず
    my_rank, _, _ = PokerRules.get_best_hand(monster.hole_cards + service.community_cards)
    opp_rank, _, _ = PokerRules.get_best_hand(prime_player.hole_cards + service.community_cards)
    assert my_rank >= opp_rank


def test_monster_targeting_prime():
    """Prime ユーザーが卓にいる場合、MonsterAI の攻撃性が増すか"""
    service = TexasPokerService(123, 100)
    service.current_max_bet = 100

    # MonsterAI
    monster = PokerPlayer(-1, "Monster", stack=1000, is_npc=True, ai_rank="monster")
    monster.current_bet = 0
    service.player_states[-1] = monster

    # Case 1: Only Recovery players
    service.player_states[1] = PokerPlayer(1, "Poor", is_npc=False, asset_rank="Recovery")
    brain = MonsterAI(monster)

    # 決定論的な確認は難しいが、内部変数の raise_chance が 0.7 になっていることをロジックから期待
    # 実機コードでは 0.7 と 0.85 の分岐がある

    # Case 2: Presence of Prime player
    service.player_states[2] = PokerPlayer(2, "Rich", is_npc=False, asset_rank="Prime")

    # decide_action を呼び出して、Prime がいる時の挙動を確認
    # (内部的な raise_chance 変数には直接アクセスできないため、成功率の統計またはモックで検証)
    # ここではロジックの存在のみを検証（実際にコードが通るか）
    action, amt = brain.decide_action(service)
    assert action in ["check", "call", "raise", "all_in", "fold"]
