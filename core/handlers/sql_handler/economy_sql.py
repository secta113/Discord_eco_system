import datetime

from .db_base import _get_connection


def log_jackpot(
    db_path: str,
    user_id: int,
    game_type: str,
    hand_name: str,
    rarity: str,
    amount: int,
    pool_after: int,
) -> None:
    """ジャックポット放出ログを記録します。

    Args:
        db_path: データベースのパス
        user_id: 放出対象のユーザーID
        game_type: ゲーム種別 (poker, blackjack etc.)
        hand_name: 役の名前
        rarity: 役の希少性
        amount: 放出金額
        pool_after: 放出後のジャックポットプール残高
    """
    jst_now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    timestamp = jst_now.isoformat()
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO jackpot_logs (timestamp, user_id, game_type, hand_name, rarity, amount, pool_after)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (timestamp, str(user_id), game_type, hand_name, rarity, amount, pool_after),
        )
        conn.commit()
