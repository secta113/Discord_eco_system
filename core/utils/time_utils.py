import datetime


def get_jst_now() -> datetime.datetime:
    """日本時間 (UTC+9) の現在時刻を返します。"""
    return datetime.datetime.utcnow() + datetime.timedelta(hours=9)


def get_jst_today() -> str:
    """日本時間の「今日」の日付を YYYY-MM-DD 形式で返します。"""
    return get_jst_now().strftime("%Y-%m-%d")


def get_jst_timestamp() -> str:
    """ログ等に利用する標準的なタイムスタンプ文字列を返します。"""
    return get_jst_now().strftime("%Y-%m-%d %H:%M:%S")
