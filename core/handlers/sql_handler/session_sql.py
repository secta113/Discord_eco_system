import json
from typing import Dict, Optional

from .db_base import _get_connection


def get_session(db_path: str, channel_id: int) -> Optional[Dict]:
    """
    指定したチャンネルで進行中のゲームセッションデータを取得します。
    """
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT session_data FROM game_sessions WHERE channel_id = ?", (str(channel_id),)
        )
        row = cursor.fetchone()

        if row and row["session_data"]:
            return json.loads(row["session_data"])
        return None


def upsert_session(
    db_path: str,
    channel_id: int,
    game_type: str,
    status: str,
    host_id: str,
    bet_amount: int,
    pot: int,
    session_data: dict,
):
    """
    ゲームセッションデータを新規作成、または更新（Upsert）します。
    """
    session_data_json = json.dumps(session_data, ensure_ascii=False)
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO game_sessions (channel_id, game_type, status, host_id, bet_amount, pot, session_data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(channel_id) DO UPDATE SET
                game_type = excluded.game_type,
                status = excluded.status,
                host_id = excluded.host_id,
                bet_amount = excluded.bet_amount,
                pot = excluded.pot,
                session_data = excluded.session_data
        """,
            (str(channel_id), game_type, status, str(host_id), bet_amount, pot, session_data_json),
        )
        conn.commit()


def delete_session(db_path: str, channel_id: int):
    """
    完了またはキャンセルされたゲームセッションデータを削除します。
    """
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM game_sessions WHERE channel_id = ?", (str(channel_id),))
        conn.commit()


def get_all_sessions(db_path: str) -> Dict[str, Dict]:
    """
    保存されているすべてのゲームセッションデータを取得します（起動時の復旧用）。
    """
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT channel_id, session_data FROM game_sessions")
        result = {}
        for row in cursor.fetchall():
            if row["session_data"]:
                result[row["channel_id"]] = json.loads(row["session_data"])
        return result
