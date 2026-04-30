import datetime
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from logic.dobumon.core.dob_battle_service import DobumonBattleService
from logic.dobumon.core.dob_exceptions import DobumonError
from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.training import WildGrowthEngine


@pytest.fixture
def mock_manager():
    return MagicMock()


@pytest.fixture
def mock_wallet():
    with patch("logic.dobumon.core.dob_battle_service.wallet") as m:
        yield m


@pytest.fixture
def battle_service(mock_manager):
    return DobumonBattleService(mock_manager)


def test_wild_battle_limit_enforced(battle_service, mock_wallet, mock_manager):
    """1日5回の制限が正しく機能するかテスト"""
    user_id = 12345
    interaction = MagicMock()
    interaction.user.id = user_id
    interaction.response = MagicMock()
    interaction.response.send_message = AsyncMock()
    interaction.edit_original_response = AsyncMock()

    # モック: attackerが存在する
    mock_attacker = MagicMock(spec=Dobumon)
    mock_attacker.owner_id = str(user_id)
    mock_attacker.is_alive = True
    mock_manager.get_dobumon.return_value = mock_attacker
    mock_manager.get_user_dobumons.return_value = [mock_attacker]

    # モック設定: 今日は5回戦い済み
    with patch("logic.dobumon.core.dob_battle_service.get_jst_today", return_value="2026-04-16"):
        mock_wallet.get_last_wild_battle_date.return_value = "2026-04-16"
        mock_wallet.get_wild_battle_count.return_value = 5

        with pytest.raises(DobumonError) as excinfo:
            import asyncio

            asyncio.run(battle_service.execute_wild_battle(interaction))

        assert "もう近くの野生はすでにドブになった" in str(excinfo.value)


def test_wild_battle_date_reset(battle_service, mock_wallet, mock_manager):
    """日付が変わったらカウントがリセットされるかテスト"""
    user_id = 12345
    interaction = MagicMock()
    interaction.user.id = user_id
    interaction.response = MagicMock()
    interaction.response.send_message = AsyncMock()
    interaction.edit_original_response = AsyncMock()
    interaction.response.is_done.return_value = False

    # 前回の記録が昨日
    with patch("logic.dobumon.core.dob_battle_service.get_jst_today", return_value="2026-04-16"):
        mock_wallet.get_last_wild_battle_date.return_value = "2026-04-15"
        mock_wallet.get_wild_battle_count.return_value = 5

        # モック: attackerが存在する
        mock_attacker = MagicMock(spec=Dobumon)
        mock_attacker.owner_id = str(user_id)
        mock_attacker.is_alive = True
        mock_manager.get_dobumon.return_value = mock_attacker
        mock_manager.get_user_dobumons.return_value = [mock_attacker]

        # モック: バトルエンジン等の回避
        with (
            patch("logic.dobumon.core.dob_battle_service.BattleEngine"),
            patch("logic.dobumon.core.dob_battle_service.BattleAutoView"),
        ):
            import asyncio

            try:
                asyncio.run(battle_service.execute_wild_battle(interaction))
            except Exception:
                pass  # Viewの初期化等で落ちるかもしれないが、制限チェック後のため無視

        # カウントリセットが呼ばれたことを確認
        mock_wallet.set_last_wild_battle_date.assert_called_with(user_id, "2026-04-16")
        mock_wallet.set_wild_battle_count.assert_called_with(user_id, 0)


def test_wild_growth_calculation():
    """3つのステータスが上昇することを確認"""
    dobu = Dobumon(
        dobumon_id="test",
        owner_id="123",
        name="Tester",
        gender="M",
        hp=100,
        atk=50,
        defense=50,
        eva=10,
        spd=20,
        attribute="fire",
    )

    # ライフステージ倍率を固定
    dobu.lifespan = 80  # Young phase

    gains = WildGrowthEngine.calculate_gains(dobu)

    # 3つのステータスが選ばれているか
    assert len(gains) == 3
    for stat, val in gains.items():
        assert stat in ["hp", "atk", "defense", "eva", "spd"]
        assert val > 0


def test_wild_growth_application():
    """上昇量が正しく反映されるか確認"""
    dobu = Dobumon(
        dobumon_id="test",
        owner_id="123",
        name="Tester",
        gender="M",
        hp=100,
        atk=50,
        defense=50,
        eva=10,
        spd=20,
        attribute="fire",
    )

    initial_stats = {"hp": 100, "atk": 50, "defense": 50, "eva": 10, "spd": 20}
    gains = {"hp": 5.5, "atk": 2.2, "spd": 1.1}

    WildGrowthEngine.apply_gains(dobu, gains)

    assert dobu.hp == 105.5
    assert dobu.atk == 52.2
    assert dobu.spd == 21.1
    assert dobu.defense == 50.0  # 上昇していない


def test_wild_battle_finish_logic_win_increments_count(battle_service, mock_wallet, mock_manager):
    """勝利時にプレイヤーの戦闘回数がインクリメントされるかテスト"""
    user_id = 12345
    dobu = MagicMock(spec=Dobumon)
    dobu.dobumon_id = "p1"
    dobu.attribute = "fire"
    dobu.name = "P1"
    dobu.win_count = 10
    dobu.today_wild_battle_count = 0
    dobu.consumption_mod = 1.0
    dobu.lifespan = 100.0

    mock_manager.settle_wild_battle.return_value = {
        "winner": "player",
        "reward": 100,
        "gains": {"hp": 1.0},
    }
    mock_wallet.load_balance.return_value = 1000
    mock_wallet.get_wild_battle_count.return_value = 2

    # _finish_wild_battle_factory から生成される関数を取得
    callback = battle_service._finish_wild_battle_factory(user_id, dobu, MagicMock(), "C", {})

    import asyncio

    asyncio.run(callback(MagicMock(), "p1", "wild"))

    # カウントが増加しているか確認
    mock_wallet.set_wild_battle_count.assert_called_with(user_id, 3)


def test_wild_battle_finish_logic_loss_no_increment(battle_service, mock_wallet, mock_manager):
    """敗北時にはプレイヤーの戦闘回数がインクリメントされないかテスト"""
    user_id = 12345
    dobu = MagicMock(spec=Dobumon)
    dobu.dobumon_id = "p1"
    dobu.attribute = "fire"
    dobu.name = "P1"
    dobu.today_wild_battle_count = 0
    dobu.consumption_mod = 1.0
    dobu.lifespan = 100.0

    mock_manager.settle_wild_battle.return_value = {"winner": "wild"}
    mock_wallet.get_wild_battle_count.return_value = 2

    callback = battle_service._finish_wild_battle_factory(user_id, dobu, MagicMock(), "C", {})

    import asyncio

    asyncio.run(callback(MagicMock(), "wild", "p1"))

    # 敗北時は勝利カウント用の set_wild_battle_count が呼ばれないことを確認
    # (初期化等で呼ばれている可能性があるため、特定の引数での呼び出し回数を確認)
    calls = [c for c in mock_wallet.set_wild_battle_count.call_args_list if c.args == (user_id, 3)]
    assert len(calls) == 0
