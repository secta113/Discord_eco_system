from unittest.mock import MagicMock

import discord
import pytest

from logic.poker.pk_view import PokerView


@pytest.fixture
def mock_session():
    # TexasPokerService の必要な属性をモック
    session = MagicMock()
    session.phase = "flop"
    session.pot = 5000
    session.current_max_bet = 1000
    session.community_cards = [("♠", "A"), ("♥", "K"), ("♦", "Q")]

    # プレイヤー情報
    p1 = {"id": 1, "name": "Player1"}
    p2 = {"id": 2, "name": "Player2"}
    session.players = [p1, p2]

    # プレイヤーステート
    s1 = MagicMock()
    s1.stack = 10000
    s1.current_bet = 500
    s1.status = "playing"
    s1.is_all_in = False

    s2 = MagicMock()
    s2.stack = 8000
    s2.current_bet = 1000
    s2.status = "playing"
    s2.is_all_in = False

    session.player_states = {1: s1, 2: s2}
    session.button_index = 0
    session.get_current_player.return_value = p2

    return session


def test_poker_view_create_embeds(mock_session):
    """PokerViewが画像用とステータス用の2つのEmbedを生成することを検証"""
    view = PokerView(mock_session)
    embeds = view._create_embeds("Player1 checked", is_game_end=False)

    # 2つのEmbedが生成されているか
    assert len(embeds) == 2

    # 1枚目: ボード用 (タイトルがある)
    assert "テキサス・ホールデム" in embeds[0].title

    # 2枚目: ステータス用 (アクションログが含まれる)
    assert embeds[1].fields[0].name == "📢 直近のアクション"
    assert "Player1 checked" in embeds[1].fields[0].value

    # 基本情報が含まれているか
    field_names = [f.name for f in embeds[1].fields]
    assert "📍 フェーズ" in field_names
    assert "💰 総ポット" in field_names
    assert "👥 参加者 (2人)" in field_names


def test_poker_view_create_embeds_showdown(mock_session):
    """ショウダウン（ゲーム終了時）のEmbed生成を検証"""
    mock_session.phase = "showdown"
    view = PokerView(mock_session)
    embeds = view._create_embeds("Game over", is_game_end=True)

    assert len(embeds) == 2
    assert "ショウダウン" in embeds[0].title


@pytest.mark.asyncio
async def test_poker_view_cache_and_upload_skip(mock_session):
    """キャッシュ判定と再アップロード抑制のロジックを検証"""
    view = PokerView(mock_session)
    view.canvas = MagicMock()
    mock_buf = MagicMock()
    mock_buf.getvalue.return_value = b"fake_img"
    view.canvas.render_table.return_value = mock_buf

    # 1. 初期状態（カードあり）での初回取得 -> 描画が実行される
    file1, changed1 = await view._get_table_file(force=True)
    assert changed1 is True
    assert file1 is not None
    assert view.canvas.render_table.call_count == 1

    # 2. 同じカード構成で再取得 -> 描画をスキップ、changed=False
    file2, changed2 = await view._get_table_file(force=False)
    assert changed2 is False
    assert file2 is None
    assert view.canvas.render_table.call_count == 1

    # 3. カードが変更された場合 -> 再描画
    mock_session.community_cards = [("♠", "A"), ("♥", "K")]
    file3, changed3 = await view._get_table_file(force=False)
    assert changed3 is True
    assert file3 is not None
    assert view.canvas.render_table.call_count == 2


@pytest.mark.asyncio
async def test_poker_view_dynamic_preflop_image(mock_session):
    """プリフロップ（空カード）時も動的に画像を生成することを検証"""
    mock_session.community_cards = []
    view = PokerView(mock_session)
    view.canvas = MagicMock()
    mock_buf = MagicMock()
    mock_buf.getvalue.return_value = b"fake_preflop_img"
    view.canvas.render_table.return_value = mock_buf

    # 初回取得 (force=True)
    file, changed = await view._get_table_file(force=True)
    assert changed is True
    assert isinstance(file, discord.File)
    assert file.filename == "table.png"
    # 動的生成なので fp は BytesIO
    assert not isinstance(file.fp, str)

    # canvas.render_table が呼ばれていること
    view.canvas.render_table.assert_called_once()

    # 同一状態での2回目呼び出し -> スキップ
    file2, changed2 = await view._get_table_file(force=False)
    assert changed2 is False
    assert file2 is None
