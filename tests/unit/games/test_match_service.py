import pytest

from logic.match.match_service import MatchService


def test_match_service_initialization():
    channel_id = 12345
    bet_amount = 500
    host_user = None

    # Normal initialization with two primary args
    session = MatchService(channel_id, bet_amount)
    assert session.channel_id == channel_id
    assert session.bet_amount == bet_amount
    assert session.game_type == "match"
    assert session.game_name == "外部マッチ"
    assert session.min_players == 2


def test_match_service_from_dict():
    channel_id = 98765
    bet_amount = 1000

    data = {
        "channel_id": channel_id,
        "bet_amount": bet_amount,
        "status": "recruiting",
        "pot": 1000,
        "players": [{"id": 111, "name": "PlayerA", "mention": "<@111>"}],
        "turn_index": 0,
        "game_type": "match",
        "host_id": "111",
    }

    # Deserializing should work gracefully due to the matching parameter order
    session = MatchService.from_dict(data)
    assert session.channel_id == channel_id
    assert session.bet_amount == bet_amount
    assert session.status == "recruiting"
    assert session.pot == 1000
    assert len(session.players) == 1
    assert session.players[0]["name"] == "PlayerA"


def test_match_service_to_dict_and_restore():
    session1 = MatchService(1, 100)
    data = session1.to_dict()

    # ensure that restoration doesn't crash on required positional arguments
    session2 = MatchService.from_dict(data)

    assert session1.channel_id == session2.channel_id
    assert session1.bet_amount == session2.bet_amount
    assert session1.status == session2.status
    assert session1.game_type == session2.game_type


def test_host_id_type_and_comparison():
    """ホストIDが数値として返り、DiscordのID(int)と正しく比較できることを検証"""
    session = MatchService(123, 100)

    # プレイヤーを追加 (IDは int)
    class MockUser:
        def __init__(self, id, name):
            self.id = id
            self.display_name = name

    user = MockUser(999888, "TestHost")
    import unittest.mock

    with unittest.mock.patch("logic.bet_service.BetService.escrow", return_value=True):
        session.add_player(user)

    # プロパティが int を返すこと
    assert session.host_id == 999888
    assert isinstance(session.host_id, int)

    # 実際の比較シナリオ (int vs int)
    assert session.host_id == user.id

    # 万が一文字列で入っていても int で返ること
    session.players[0]["id"] = "123456"
    assert session.host_id == 123456
    assert isinstance(session.host_id, int)
