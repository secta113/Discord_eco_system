import sys

from core.utils.time_utils import get_jst_timestamp


class Logger:
    """
    システム全体のログ出力を管理するクラス。
    JSTタイムスタンプを自動付与し、標準出力に表示します。
    """

    @staticmethod
    def _log(level: str, module: str, message: str):
        # 共通ユーティリティから JST タイムスタンプを取得
        timestamp = get_jst_timestamp()

        # フォーマット: [Timestamp] [LEVEL] [Module] Message
        formatted_msg = f"[{timestamp}] [{level.ljust(5)}] [{module}] {message}"
        print(formatted_msg)
        sys.stdout.flush()  # Raspberry Pi等でのバッファリング対策

    @staticmethod
    def info(module: str, message: str):
        Logger._log("INFO", module, message)

    @staticmethod
    def warn(module: str, message: str):
        Logger._log("WARN", module, message)

    @staticmethod
    def error(module: str, message: str):
        Logger._log("ERROR", module, message)

    @staticmethod
    def debug(module: str, message: str):
        Logger._log("DEBUG", module, message)
