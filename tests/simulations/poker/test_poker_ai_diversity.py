import random
import unittest.mock
from unittest.mock import MagicMock

import pytest

from logic.poker.ai.brains import CommonAI, MonsterAI
from logic.poker.ai.personality import apply_personality
from logic.poker.pk_models import PokerPlayer
from logic.poker.pk_rules import PokerRules


class TestPokerAIDiversity:
    def test_poker_player_serialization_with_risk(self):
        """risk_levelと性格タイプが正しくシリアライズされるか検証"""
        p = PokerPlayer(1, "Test", risk_level=0.8, personality="shark", stack=10000)
        data = p.to_dict()
        assert data["risk_level"] == 0.8
        assert data["personality"] == "shark"

        p2 = PokerPlayer.from_dict(data)
        assert p2.risk_level == 0.8
        assert p2.personality == "shark"

    def test_risk_level_influence_on_folding(self):
        """リスク許容度がフォールド判断に影響を与えるか検証"""
        session = MagicMock()
        session.current_max_bet = 1000
        session.pot = 2000
        session.big_blind = 100
        session.table_average_stack = 2000  # weight = 0.5

        # normal性格で比較
        p_low_risk = PokerPlayer(1, "Low", risk_level=0.1, personality="normal", stack=10000)
        p_high_risk = PokerPlayer(2, "High", risk_level=0.9, personality="normal", stack=10000)
        p_low_risk.current_bet = 0
        p_high_risk.current_bet = 0

        # 乱数 0.4 の場合:
        # low_risk(0.1): mult=1.4, chance=0.45*1.4=0.63 -> 0.4 < 0.63 -> Fold
        # high_risk(0.9): mult=0.6, chance=0.45*0.6=0.27 -> 0.4 < 0.27 -> False -> Call
        with unittest.mock.patch("logic.poker.ai.personality.random.random", return_value=0.4):
            act_low, _ = apply_personality("call", 0, session, p_low_risk)
            act_high, _ = apply_personality("call", 0, session, p_high_risk)

            assert act_low == "fold"
            assert act_high == "call"

    def test_station_personality(self):
        """Calling Station性格が重いベットでも中々降りないことを検証"""
        session = MagicMock()
        session.current_max_bet = 5000
        session.table_average_stack = 2000  # weight=2.5
        p = PokerPlayer(1, "Station", personality="station", risk_level=0.5, stack=10000)
        p.current_bet = 0

        # Stationのフォールド率は基本 0.05 * 1.0 = 0.05
        # 乱数 0.1 なら降りない
        with unittest.mock.patch("logic.poker.ai.personality.random.random", return_value=0.1):
            action, _ = apply_personality("call", 0, session, p)
            assert action == "call"

    def test_monster_ai_ignores_personality_but_uses_risk(self):
        """MonsterAIが性格(timid)を無視しつつ、risk_levelでレイズ額を変えるか検証"""
        session = MagicMock()
        session.current_max_bet = 400
        session.big_blind = 100
        session.community_cards = []
        session.pot = 5000  # ポットを大きくして rational な fold を防ぐ
        session.table_average_stack = 2000  # weight = 400/2000 = 0.2

        p_monster = PokerPlayer(
            666, "Monster", personality="timid", risk_level=0.9, ai_rank="monster", stack=10000
        )
        p_monster.hole_cards = [("♠", "A"), ("♣", "A")]

        p_human = PokerPlayer(1, "Human", is_npc=False)
        p_human.hole_cards = [("♥", "A"), ("♦", "A")]
        p_human.status = "playing"

        session.player_states = {666: p_monster, 1: p_human}

        ai = MonsterAI(p_monster)

        # 1. risk_level=0.9 によるレイズ額 (multiplier = 3 + 4 = 7)
        # target = 400 + 100 * 7 = 1100
        # 人間のほうが強いフリをする (イカサマ条件)
        with unittest.mock.patch(
            "logic.poker.ai.brains.PokerRules.get_best_hand_provisional"
        ) as mock_rules:
            mock_rules.side_effect = lambda cards: (
                (3, [14], "Win") if ("♥", "A") in cards else (2, [14], "Pair")
            )

            # 1. 1回目の random.random() で [レイズすること] を、
            #    2回目の random.random() で [特大レイズ(roll >= 0.7)] を選択させる
            #   (risk_level=0.9 -> multiplier = 5 + int(0.9 * 3) = 7)
            #   target = 400 + 100 * 7 = 1100
            with unittest.mock.patch("logic.poker.ai.brains.random.random", side_effect=[0.0, 0.8]):
                action, amt = ai.decide_action(session)
                assert action == "raise"
                assert amt == 1100

            # 2. 性格(timid)の無視を検証
            # weight=0.2, timid(mult=1.4) なら fold_chance = 0.2*3*1.4 = 0.84
            # 乱数 0.5 なら本来 timid は降りるが、MonsterAIは降りない (AAのEquity=0.8 > Odds=0.07)
            with unittest.mock.patch("logic.poker.ai.brains.random.random", return_value=0.5):
                with unittest.mock.patch.object(ai, "get_hand_strength", return_value=0.9):
                    res_action, _ = ai.decide_action(session)
                    # もし timid が効いていれば apply_personality が呼ばれて "fold" になる
                    # バイパスされていれば LegendaryAI._get_base_action により "call" または "raise" になる
                    assert res_action != "fold"
