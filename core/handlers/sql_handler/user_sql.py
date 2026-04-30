import datetime
import json
from typing import Dict, Optional

from .db_base import _get_connection


def get_user(db_path: str, user_id: int) -> Optional[Dict]:
    """
    指定したユーザーの口座情報を取得します。
    """
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM wallets WHERE user_id = ?", (str(user_id),))
        row = cursor.fetchone()

        if row:
            history = []
            if row["history"]:
                history = json.loads(row["history"])

            gacha_collection = []
            if row["gacha_collection"]:
                gacha_collection = json.loads(row["gacha_collection"])

            return {
                "balance": row["balance"],
                "last_daily": row["last_daily"],
                "last_gacha_daily": row["last_gacha_daily"],
                "gacha_collection": gacha_collection,
                "history": history,
                "total_wins": row["total_wins"] or 0,
                "games_played": row["games_played"] or 0,
                "max_win_amount": row["max_win_amount"] or 0,
                "gacha_count_today": row["gacha_count_today"] or 0,
                "last_wild_battle_date": row["last_wild_battle_date"] or "1970-01-01",
                "wild_battle_count_today": row["wild_battle_count_today"] or 0,
                "dob_buy_data": json.loads(row["dob_buy_data"]) if row["dob_buy_data"] else {},
            }
        return None


def upsert_user(
    db_path: str,
    user_id: int,
    balance: int,
    last_daily: str,
    history: list = None,
    total_wins: int = 0,
    games_played: int = 0,
    max_win_amount: int = 0,
    last_gacha_daily: str = None,
    gacha_collection: list = None,
    gacha_count_today: int = 0,
    last_wild_battle_date: str = "1970-01-01",
    wild_battle_count_today: int = 0,
    dob_buy_data: dict = None,
):
    """
    ユーザーの口座情報を新規作成、または更新（Upsert）します。
    """
    jst_now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    updated_at = jst_now.isoformat()
    history_json = json.dumps(history or [], ensure_ascii=False)
    gacha_collection_json = json.dumps(gacha_collection or [], ensure_ascii=False)
    dob_buy_data_json = json.dumps(dob_buy_data or {}, ensure_ascii=False)
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO wallets (user_id, balance, last_daily, last_gacha_daily, gacha_collection, updated_at, history, total_wins, games_played, max_win_amount, gacha_count_today, last_wild_battle_date, wild_battle_count_today, dob_buy_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                balance = excluded.balance,
                last_daily = excluded.last_daily,
                last_gacha_daily = excluded.last_gacha_daily,
                gacha_collection = excluded.gacha_collection,
                updated_at = excluded.updated_at,
                history = excluded.history,
                total_wins = excluded.total_wins,
                games_played = excluded.games_played,
                max_win_amount = excluded.max_win_amount,
                gacha_count_today = excluded.gacha_count_today,
                last_wild_battle_date = excluded.last_wild_battle_date,
                wild_battle_count_today = excluded.wild_battle_count_today,
                dob_buy_data = excluded.dob_buy_data
        """,
            (
                str(user_id),
                balance,
                last_daily,
                last_gacha_daily,
                gacha_collection_json,
                updated_at,
                history_json,
                total_wins,
                games_played,
                max_win_amount,
                gacha_count_today,
                last_wild_battle_date,
                wild_battle_count_today,
                dob_buy_data_json,
            ),
        )
        conn.commit()


def delete_user(db_path: str, user_id: int):
    """
    指定したユーザーの情報をデータベースから削除します。
    """
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM wallets WHERE user_id = ?", (str(user_id),))
        conn.commit()


def get_all_users(db_path: str) -> Dict[int, Dict]:
    """
    全ユーザーの口座情報を取得します（ランキング等での利用を想定）。
    user_id = '0' はシステム口座(ジャックポット等用)なので除外します。
    """
    result = {}
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM wallets WHERE user_id != '0'")
        for row in cursor.fetchall():
            try:
                uid = int(row["user_id"])

                history = []
                if row["history"]:
                    history = json.loads(row["history"])

                gacha_collection = []
                if row["gacha_collection"]:
                    gacha_collection = json.loads(row["gacha_collection"])

                result[uid] = {
                    "balance": row["balance"],
                    "last_daily": row["last_daily"],
                    "last_gacha_daily": row["last_gacha_daily"],
                    "gacha_collection": gacha_collection,
                    "history": history,
                    "total_wins": row["total_wins"] or 0,
                    "games_played": row["games_played"] or 0,
                    "max_win_amount": row["max_win_amount"] or 0,
                    "gacha_count_today": row["gacha_count_today"] or 0,
                    "last_wild_battle_date": row["last_wild_battle_date"] or "1970-01-01",
                    "wild_battle_count_today": row["wild_battle_count_today"] or 0,
                    "dob_buy_data": json.loads(row["dob_buy_data"]) if row["dob_buy_data"] else {},
                }
            except ValueError:
                pass
    return result
