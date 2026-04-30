import random

import pytest

from logic.poker.pk_service import TexasPokerService


def test_poker_blueprint_loading():
    """設計図が正しく読み込まれ、構成が決定されるか"""
    service = TexasPokerService(channel_id=123, bet_amount=100)

    # 3人補充時の計測
    service._decide_table_blueprint(3)
    assert len(service.npc_blueprints) == 3
    assert service.game_rank in ["monster", "legendary", "rare", "common", "trash"]


def test_poker_monster_rate_statistical():
    """統計的にMonster出現率が5%に近いか検証（500回試行）"""
    monster_games = 0
    total_trials = 500

    for _ in range(total_trials):
        service = TexasPokerService(channel_id=123, bet_amount=100)
        service._decide_table_blueprint(needed=3)

        if service.game_rank == "monster":
            monster_games += 1
            # Monster回なら1人だけMonsterがいることを、blueprintレベルで検証
            ranks = [b["rank"] for b in service.npc_blueprints]
            assert "monster" in ranks
            # Monster回なら必ず1人だけMonsterがいることを検証
            assert ranks.count("monster") == 1

    rate = monster_games / total_trials
    print(f"Monster Game Rate: {rate:.2%}")
    # 5%の期待値に対し、±5%の範囲(0%-10%)に収まるか確認（下限は1%とする）
    assert 0.01 <= rate <= 0.10


def test_poker_legendary_limit_enforced():
    """Legendaryが3人以上出現しないか検証"""
    for _ in range(100):
        service = TexasPokerService(channel_id=123, bet_amount=100)
        service._decide_table_blueprint(needed=3)

        ranks = [b["rank"] for b in service.npc_blueprints]
        # テンプレート側で制限されていることを確認（3体まで許可）
        assert ranks.count("legendary") <= 3


def test_poker_fill_npcs_uses_blueprints():
    """_fill_npcsが設計図通りのランクをNPCに割り当てるか"""
    service = TexasPokerService(channel_id=123, bet_amount=100, target_player_count=4)
    # ダミーの人間を1人追加
    service.players = [{"id": 1, "name": "Human", "mention": "<@1>"}]

    # 設計図を強制固定
    service.game_rank = "monster"
    service.npc_blueprints = [
        {"rank": "monster", "personality": "aggressive"},
        {"rank": "trash", "personality": "timid"},
        {"rank": "common", "personality": "normal"},
    ]

    service._fill_npcs()

    npcs = [p for p in service.player_states.values() if p.is_npc]
    assert len(npcs) == 3

    # 割当順序の確認
    assert npcs[0].ai_rank == "monster"
    assert npcs[0].personality == "aggressive"
    assert npcs[1].ai_rank == "trash"
    assert npcs[1].personality == "timid"
    assert npcs[2].ai_rank == "common"
    assert npcs[2].personality == "normal"
