import os
import unittest.mock
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

# テスト実行中は常に APP_ENV=test を設定
os.environ["APP_ENV"] = "test"

# DIコンフィグを初期化して、インポート時に本番DBを参照しないようにする
worker_id = os.environ.get("PYTEST_XDIST_WORKER")
if not worker_id:
    worker_id = "master"
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_test_db_path = os.path.join(base_dir, "data", f"test_db_{worker_id}.db")

from core.handlers.storage import DatabaseConfig

DatabaseConfig.set_db_path(_test_db_path)


@pytest.fixture(scope="session")
def worker_id_cached(request):
    """pytest-xdistがインストールされていない場合の回避策"""
    if hasattr(request.config, "workerinput"):
        return request.config.workerinput["workerid"]
    return "master"


@pytest.fixture(scope="session")
def test_db_path(worker_id_cached):
    """
    並列実行に対応したDBパスの提供。
    ワーカーごとに個別のDBファイル名を作成する。
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base_dir, "data", f"test_db_{worker_id_cached}.db")
    return path


@pytest.fixture(autouse=True)
def init_test_env(test_db_path):
    """
    テストごとの初期化。
    指定されたDBファイルをクリーンな状態で開始する。
    """
    from core.economy import wallet
    from core.handlers.storage import (
        SQLiteDobumonRepository,
        SQLiteSessionRepository,
        SQLiteSystemRepository,
        SQLiteUserRepository,
    )
    from managers.manager import game_manager

    # 既存のテスト用DBを初期化 (ファイルロック対策としてDELETEクエリを実行)
    if os.path.exists(test_db_path):
        try:
            import sqlite3

            with sqlite3.connect(test_db_path) as conn:
                conn.execute("DELETE FROM wallets;")
                conn.execute("DELETE FROM game_sessions;")
                conn.execute("DELETE FROM jackpot_logs;")
                conn.execute("DELETE FROM system_stats;")
                conn.execute("DELETE FROM dobumons;")
                conn.commit()
        except Exception:
            try:
                os.remove(test_db_path)
            except Exception:
                pass

    # walletとgame_managerのリポジトリをテスト用パスで確実に再初期化
    wallet.user_repo = SQLiteUserRepository(test_db_path)
    wallet.system_repo = SQLiteSystemRepository(test_db_path)
    game_manager.session_repo = SQLiteSessionRepository(test_db_path)

    # sql_handler.init_db はリポジトリのコンストラクタ内で呼ばれるが、念のため
    from core.handlers import sql_handler

    sql_handler.init_db(test_db_path)

    # JackpotService の TC キャッシュをテストごとにリセットして独立性を確保
    from logic.economy.jackpot import JackpotService

    # キャッシュを常に無効化する (本番コード内に APP_ENV の分岐を含まないための措置)
    JackpotService.TC_CACHE_TTL = -1

    with JackpotService._tc_lock:
        JackpotService._tc_cache = None
        JackpotService._tc_cache_time = 0

    yield


def pytest_unconfigure(config):
    """テストセッション終了時に、全ワーカーの一時DBファイルを一括削除する"""
    if hasattr(config, "workerinput"):
        # ワーカープロセス内では何もしない
        return

    # メインプロセスでのみ実行
    import glob

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pattern = os.path.join(base_dir, "data", "test_db*.db")
    for f in glob.glob(pattern):
        try:
            # 他のプロセスが閉じきるのを待つため、数回リトライ
            for _ in range(3):
                try:
                    os.remove(f)
                    break
                except Exception:
                    import time

                    time.sleep(0.5)
        except Exception:
            pass


@pytest.fixture
def mock_wallet():
    """walletの各メソッドをMagicMock化する。"""
    with unittest.mock.patch("core.economy.wallet") as m:
        yield m


@pytest.fixture
def mock_bet_service():
    """BetServiceの各メソッドをMagicMock化する。"""
    with unittest.mock.patch("logic.bet_service.BetService") as m:
        yield m


@pytest.fixture
def mock_interaction():
    """discord.Interactionのモックオブジェクトを作成する。"""
    interaction = MagicMock(spec=discord.Interaction)
    # response.send_message
    interaction.response = MagicMock()
    interaction.response.send_message = AsyncMock(return_value=None)
    interaction.response.defer = AsyncMock(return_value=None)
    interaction.response.edit_message = AsyncMock(return_value=None)
    # followup.send
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock(return_value=MagicMock(spec=discord.Message))

    # edit_original_response / edit_message
    interaction.edit_original_response = AsyncMock(return_value=None)

    # channel モック
    interaction.channel = MagicMock()
    interaction.channel.send = AsyncMock(return_value=MagicMock(spec=discord.Message))
    interaction.channel.id = 900000000 + (id(interaction) % 100000000)

    # User (Member) モック
    interaction.user = MagicMock()
    interaction.user.id = 123456789
    interaction.user.display_name = "TestUser"
    interaction.user.mention = "<@123456789>"

    # Guild モック
    interaction.guild = MagicMock()
    interaction.guild.id = 888222333
    interaction.guild.get_member = MagicMock(return_value=interaction.user)

    # ID系モック (重複回避のため id(interaction) をベースにする)
    interaction.channel_id = 900000000 + (id(interaction) % 100000000)
    interaction.guild_id = interaction.guild.id

    return interaction


@pytest.fixture
def mock_button():
    """discord.ui.Buttonのモックオブジェクトを作成する。"""
    button = MagicMock(spec=discord.ui.Button)
    button.disabled = False
    return button
