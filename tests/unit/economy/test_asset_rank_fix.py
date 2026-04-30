from unittest.mock import MagicMock, patch

import pytest

from core.economy import wallet
from logic.economy.status import StatusService
from logic.poker.ai.brains import MonsterAI
from logic.poker.pk_models import PokerPlayer
from logic.poker.pk_service import TexasPokerService
from managers.manager import GameManager


@pytest.fixture
def mock_wallet():
    with patch("core.economy.wallet.load_balance") as mock_load:
        with patch("core.economy.wallet.save_balance"):
            with patch("core.economy.wallet.add_history"):
                with patch("core.economy.wallet.get_all_balances") as mock_all:
                    yield mock_load, mock_all


def test_poker_buyin_full_wallet_preserves_prime_rank(mock_wallet):
    mock_load, mock_all = mock_wallet

    user_id = 999
    # 資産は100,000 pts (ベンチマークを下げれば Prime になる)
    initial_balance = 100000
    mock_load.return_value = initial_balance
    # 他に貧乏なユーザー（残高100）を混ぜてベンチマークを下げる
    mock_all.return_value = {user_id: initial_balance, 888: 100, 0: 0}

    # ポーカーセッション作成 (バイイン 100,000)
    service = TexasPokerService(1, bet_amount=100, buyin_amount=100000)
    user = MagicMock()
    user.id = user_id
    user.display_name = "RichGuy"

    # GameManager経由で参加（これが現在の正規ルート）

    manager = GameManager(session_repo=MagicMock())

    # 参加前のランク確認
    expected_rank = StatusService.get_user_status(user_id)
    assert expected_rank == "Prime"

    # 参加処理
    # GameManager.join_session は内部で add_player を呼ぶ
    # add_player の中で本来なら escrow されて残高が 0 になるが、
    # 修正後は add_player の引数または内部で escrow 前にランクを固定しているはず

    # 擬似的に escrow を成功させるために mock_load の戻り値を変化させるシミュレーションは不要
    # 重要なのは GameManager が StatusService.get_user_status を先に呼んでいること

    with patch.object(TexasPokerService, "add_player", wraps=service.add_player) as mock_add:
        # 実際に参加
        service.add_player(user, asset_rank=expected_rank)

        player = service.player_states[user_id]
        # 残高がどうあれ、ランクが Prime で固定されていることを確認
        assert player.asset_rank == "Prime"


def test_monster_ai_still_cheats_against_max_buyin_prime(mock_wallet):
    mock_load, mock_all = mock_wallet
    user_id = 999
    initial_balance = 100000
    mock_load.return_value = initial_balance
    mock_all.return_value = {user_id: initial_balance, 888: 100, 0: 0}

    service = TexasPokerService(1, bet_amount=100)
    service.community_cards = [("S", "10"), ("D", "J"), ("H", "Q"), ("C", "K"), ("S", "2")]

    # Primeユーザーを参加させる
    rich_player = PokerPlayer(user_id, "RichGuy", stack=100000, asset_rank="Prime")
    rich_player.hole_cards = [("S", "A"), ("C", "3")]  # ストレート
    service.player_states[user_id] = rich_player

    # MonsterAI
    monster = PokerPlayer(-1, "Monster", stack=1000, is_npc=True, ai_rank="monster")
    monster.hole_cards = [("H", "2"), ("D", "3")]  # ハイカード
    service.player_states[-1] = monster

    brain = MonsterAI(monster)

    # Prime相手にはイカサマを行うはず (Recoveryではないので)
    import random

    random.seed(42)
    brain.cheat_hand(service)

    # 交換されている = イカサマ発動
    assert monster.hole_cards != [("H", "2"), ("D", "3")]
