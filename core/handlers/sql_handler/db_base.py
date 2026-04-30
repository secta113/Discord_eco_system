import datetime
import json
import sqlite3
from typing import Any, Dict, Optional


def _get_connection(db_path: str) -> sqlite3.Connection:
    """
    指定されたSQLiteデータベースへのコネクションを生成して返します。
    辞書のようにカラム名でアクセスできるよう row_factory を設定しています。
    """
    conn = sqlite3.connect(db_path, timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db(db_path: str):
    """
    データベースの初期化を行います。
    必要なテーブル（wallets, game_sessions）が存在しない場合は作成します。
    """
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        # ユーザー口座情報テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wallets (
                user_id TEXT PRIMARY KEY,
                balance INTEGER NOT NULL,
                last_daily TEXT,
                last_gacha_daily TEXT,
                gacha_collection TEXT,
                updated_at TEXT,
                history TEXT,
                total_wins INTEGER DEFAULT 0,
                games_played INTEGER DEFAULT 0,
                max_win_amount INTEGER DEFAULT 0,
                gacha_count_today INTEGER DEFAULT 0,
                last_wild_battle_date TEXT DEFAULT '1970-01-01',
                wild_battle_count_today INTEGER DEFAULT 0,
                dob_buy_data TEXT
            )
        """)

        _migrate_wallets(cursor)

        # ゲーム進行状態テーブル (Bot再起動復旧用)
        # ゲーム進行状態テーブル (Bot再起動復旧用)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_sessions (
                channel_id TEXT PRIMARY KEY,
                game_type TEXT,
                status TEXT,
                host_id TEXT,
                bet_amount INTEGER,
                pot INTEGER,
                session_data TEXT
            )
        """)
        conn.commit()

        # ジャックポット放出ログテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jackpot_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                user_id TEXT,
                game_type TEXT,
                hand_name TEXT,
                rarity TEXT,
                amount INTEGER,
                pool_after INTEGER
            )
        """)
        conn.commit()

        # システム設定・統計テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_stats (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # 怒武者（ドブモン）テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dobumons (
                dobumon_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                name TEXT NOT NULL,
                gender TEXT NOT NULL,
                hp INTEGER NOT NULL,
                atk INTEGER NOT NULL,
                defense INTEGER NOT NULL,
                eva INTEGER NOT NULL,
                spd INTEGER NOT NULL,
                health INTEGER DEFAULT 0,
                skills TEXT,
                iv TEXT,
                lifespan REAL,
                is_alive INTEGER DEFAULT 1,
                attribute TEXT,
                affection INTEGER DEFAULT 0,
                genetics TEXT,
                win_count INTEGER DEFAULT 0,
                rank INTEGER DEFAULT 0,
                generation INTEGER DEFAULT 1,
                is_sterile INTEGER DEFAULT 0,
                can_extend_lifespan INTEGER DEFAULT 1,
                illness_rate REAL DEFAULT 0.01,
                today_affection_gain INTEGER DEFAULT 0,
                today_wild_battle_count INTEGER DEFAULT 0,
                today_massage_count INTEGER DEFAULT 0,
                max_lifespan REAL DEFAULT 100,
                lineage TEXT,
                traits TEXT,
                last_train_date TEXT DEFAULT '1970-01-01',
                today_train_count INTEGER DEFAULT 0,
                is_sold INTEGER DEFAULT 0,
                shop_flags TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        _migrate_dobumons(cursor)

        # health の不整合修正マイグレーション: 0 以下の値を hp (フルHP) として復元

        # health の不整合修正マイグレーション: 0 以下の値を hp (フルHP) として復元
        cursor.execute("UPDATE dobumons SET health = hp WHERE health <= 0")

        conn.commit()
        repair_legacy_dobumons(conn)


def _migrate_wallets(cursor: sqlite3.Cursor) -> None:
    """wallets テーブルのマイグレーションを行います。"""
    cursor.execute("PRAGMA table_info(wallets)")
    columns = [col["name"] for col in cursor.fetchall()]
    if "history" not in columns:
        cursor.execute("ALTER TABLE wallets ADD COLUMN history TEXT")
    if "total_wins" not in columns:
        cursor.execute("ALTER TABLE wallets ADD COLUMN total_wins INTEGER DEFAULT 0")
    if "games_played" not in columns:
        cursor.execute("ALTER TABLE wallets ADD COLUMN games_played INTEGER DEFAULT 0")
    if "max_win_amount" not in columns:
        cursor.execute("ALTER TABLE wallets ADD COLUMN max_win_amount INTEGER DEFAULT 0")
    if "last_gacha_daily" not in columns:
        cursor.execute("ALTER TABLE wallets ADD COLUMN last_gacha_daily TEXT")
    if "gacha_collection" not in columns:
        cursor.execute("ALTER TABLE wallets ADD COLUMN gacha_collection TEXT")
    if "gacha_count_today" not in columns:
        cursor.execute("ALTER TABLE wallets ADD COLUMN gacha_count_today INTEGER DEFAULT 0")
    if "last_wild_battle_date" not in columns:
        cursor.execute(
            "ALTER TABLE wallets ADD COLUMN last_wild_battle_date TEXT DEFAULT '1970-01-01'"
        )
    if "wild_battle_count_today" not in columns:
        cursor.execute("ALTER TABLE wallets ADD COLUMN wild_battle_count_today INTEGER DEFAULT 0")
    if "dob_buy_data" not in columns:
        cursor.execute("ALTER TABLE wallets ADD COLUMN dob_buy_data TEXT")


def _migrate_dobumons(cursor: sqlite3.Cursor) -> None:
    """dobumons テーブルのマイグレーションを行います。"""
    cursor.execute("PRAGMA table_info(dobumons)")
    columns = [col["name"] for col in cursor.fetchall()]
    if "last_train_date" not in columns:
        cursor.execute("ALTER TABLE dobumons ADD COLUMN last_train_date TEXT DEFAULT '1970-01-01'")
    if "today_train_count" not in columns:
        cursor.execute("ALTER TABLE dobumons ADD COLUMN today_train_count INTEGER DEFAULT 0")
    if "is_sterile" not in columns:
        cursor.execute("ALTER TABLE dobumons ADD COLUMN is_sterile INTEGER DEFAULT 0")
    if "can_extend_lifespan" not in columns:
        cursor.execute("ALTER TABLE dobumons ADD COLUMN can_extend_lifespan INTEGER DEFAULT 1")
    if "illness_rate" not in columns:
        cursor.execute("ALTER TABLE dobumons ADD COLUMN illness_rate REAL DEFAULT 0.01")
    if "today_affection_gain" not in columns:
        cursor.execute("ALTER TABLE dobumons ADD COLUMN today_affection_gain INTEGER DEFAULT 0")
    if "generation" not in columns:
        cursor.execute("ALTER TABLE dobumons ADD COLUMN generation INTEGER DEFAULT 1")
    if "lineage" not in columns:
        cursor.execute("ALTER TABLE dobumons ADD COLUMN lineage TEXT")
    if "traits" not in columns:
        cursor.execute("ALTER TABLE dobumons ADD COLUMN traits TEXT")
    if "today_wild_battle_count" not in columns:
        cursor.execute("ALTER TABLE dobumons ADD COLUMN today_wild_battle_count INTEGER DEFAULT 0")
    if "today_massage_count" not in columns:
        cursor.execute("ALTER TABLE dobumons ADD COLUMN today_massage_count INTEGER DEFAULT 0")
    if "max_lifespan" not in columns:
        cursor.execute("ALTER TABLE dobumons ADD COLUMN max_lifespan REAL DEFAULT 100")
    if "shop_flags" not in columns:
        cursor.execute("ALTER TABLE dobumons ADD COLUMN shop_flags TEXT")
    if "is_sold" not in columns:
        cursor.execute("ALTER TABLE dobumons ADD COLUMN is_sold INTEGER DEFAULT 0")


def repair_legacy_dobumons(conn: sqlite3.Connection) -> None:
    """遺伝子情報を持たない旧データのドブモンに対し、初期データ（野生種相当の遺伝子・IV等）を付与します。
    Bot起動時に一度だけ実行され、新システムへの互換性を確保します。

    Args:
        conn: SQLite データベース接続オブジェクト
    """
    import random

    cursor = conn.cursor()
    cursor.execute(
        "SELECT dobumon_id, genetics, traits, iv FROM dobumons WHERE genetics IS NULL OR traits IS NULL OR iv IS NULL OR genetics = '{}'"
    )
    rows = cursor.fetchall()

    if not rows:
        return

    for row in rows:
        did = row["dobumon_id"]

        # 1. 遺伝型の生成 (野生種相当)
        genotype = {
            "growth": ["D", "r"],
            "vitality": ["D", "r"],
            "potential": ["D", "r"],
            "body": ["D", "r"],
        }

        # 2. 特性の解決 (簡易版)
        traits = ["early", "hardy", "stable", "normal"]  # D 側の特性をデフォルト付与

        # 3. IVの補完 (既に値があれば維持、なければ平均)
        current_iv: Dict[str, float] = {}
        if row["iv"]:
            try:
                current_iv = json.loads(row["iv"])
            except Exception:
                pass

        if not current_iv:
            current_iv = {
                k: round(random.uniform(0.9, 1.1), 2)
                for k in ["hp", "atk", "defense", "eva", "spd"]
            }

        # 4. 更新
        genetics_json = json.dumps({"genotype": genotype}, ensure_ascii=False)
        traits_json = json.dumps(traits, ensure_ascii=False)
        iv_json = json.dumps(current_iv, ensure_ascii=False)
        lineage_json = json.dumps([], ensure_ascii=False)

        cursor.execute(
            "UPDATE dobumons SET genetics = ?, traits = ?, iv = ?, lineage = IFNULL(lineage, ?) WHERE dobumon_id = ?",
            (genetics_json, traits_json, iv_json, lineage_json, did),
        )

    conn.commit()


def get_system_stats(db_path: str, key: str) -> Optional[Dict[str, Any]]:
    """システム全体の設定や統計情報を取得します。

    Args:
        db_path: データベースのパス
        key: 取得する情報のキー

    Returns:
        Optional[Dict[str, Any]]: 格納されたデータの辞書。存在しない場合は None。
    """
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM system_stats WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row and row["value"]:
            return json.loads(row["value"])
        return None


def upsert_system_stats(db_path: str, key: str, value: Dict[str, Any]) -> None:
    """システム全体の設定や統計情報を保存・更新します。

    Args:
        db_path: データベースのパス
        key: 保存する情報のキー
        value: 保存するデータの辞書
    """
    value_json = json.dumps(value or {}, ensure_ascii=False)
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO system_stats (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
            (key, value_json),
        )
        conn.commit()
