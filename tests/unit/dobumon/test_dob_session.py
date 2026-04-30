from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from core.handlers.storage import ISessionRepository
from core.models.validation import SessionSchemaType
from logic.dobumon.dob_battle.battle_session import DobumonBattleSession
from managers.manager import GameActionError, GameManager


@pytest.fixture
def mock_repo():
    repo = MagicMock(spec=ISessionRepository)
    repo.get_session.return_value = None
    return repo


@pytest.fixture
def game_manager(mock_repo):
    return GameManager(session_repo=mock_repo)


@pytest.fixture
def mock_user():
    user = MagicMock(spec=discord.Member)
    user.id = 123
    user.display_name = "TestUser"
    return user


@pytest.fixture
def mock_dobumon():
    dobu = MagicMock()
    dobu.dobumon_id = "dobu_1"
    dobu.name = "TestDobu"
    dobu.owner_id = "123"
    dobu.to_dict.return_value = {
        "dobumon_id": "dobu_1",
        "owner_id": "123",
        "name": "TestDobu",
        "gender": "M",
        "hp": 100.0,
        "atk": 50.0,
        "defense": 50.0,
        "eva": 10.0,
        "spd": 10.0,
    }
    return dobu


def test_dobumon_session_serialization():
    """セッションのシリアライズ・デシリアライズ検証"""
    session = DobumonBattleSession(channel_id=456)
    session.attacker_data = {"id": "a"}
    session.defender_data = {"id": "d"}
    session.steps = [{"turn": 0}]
    session.winner_id = "a"
    session.status = "playing"

    data = session.to_dict()
    assert data["game_type"] == "dobumon_battle"
    assert data["attacker_data"] == {"id": "a"}

    restored = DobumonBattleSession.from_dict(data)
    assert restored.channel_id == 456
    assert restored.attacker_data == {"id": "a"}
    assert restored.status == "playing"


def test_create_dobumon_battle_logic(game_manager, mock_user, mock_dobumon):
    """セッション作成時のバリデーション検証"""
    # 正常作成
    session, msg = game_manager.create_dobumon_battle(
        channel_id=789,
        user=mock_user,
        attacker=mock_dobumon,
        defender=mock_dobumon,
        steps=[],
        winner_id="w",
        loser_id="l",
    )
    assert session is not None
    assert msg == "success"
    assert game_manager.session_repo.save_session.called

    # 重複作成の防止
    from pydantic import TypeAdapter

    adapter = TypeAdapter(SessionSchemaType)
    model = adapter.validate_python(session.to_dict())
    game_manager.session_repo.get_session.return_value = model
    session2, msg2 = game_manager.create_dobumon_battle(
        channel_id=789,
        user=mock_user,
        attacker=mock_dobumon,
        defender=mock_dobumon,
        steps=[],
        winner_id="w",
        loser_id="l",
    )
    assert session2 is None
    assert "別のゲームが進行中です" in msg2


@pytest.mark.asyncio
async def test_cancel_dobumon_battle(game_manager, mock_user, mock_dobumon):
    """dd-cancel (GameManager.end_session) によるセッション破棄検証"""
    channel_id = 1010
    session, _ = game_manager.create_dobumon_battle(
        channel_id=channel_id,
        user=mock_user,
        attacker=mock_dobumon,
        defender=mock_dobumon,
        steps=[],
        winner_id="w",
        loser_id="l",
    )

    # セッションが存在することを確認
    from pydantic import TypeAdapter

    adapter = TypeAdapter(SessionSchemaType)
    model = adapter.validate_python(session.to_dict())
    game_manager.session_repo.get_session.return_value = model
    assert game_manager.get_session(channel_id) is not None

    # セッション終了（cancel実行時を想定）
    game_manager.end_session(channel_id)
    assert game_manager.session_repo.delete_session.called

    # 削除後の確認（モックの戻り値をNoneに変更）
    game_manager.session_repo.get_session.return_value = None
    assert game_manager.get_session(channel_id) is None
