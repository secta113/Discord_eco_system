import logging
import os
import sys

from core.utils.time_utils import get_jst_timestamp

# ロギングの初期設定
# JSTタイムスタンプは自前のフォーマットで対応するか、loggingのFormatterを拡張できますが、
# 今回は既存のフォーマット `[Timestamp] [LEVEL] [Module] Message` を保つために
# カスタムFormatterを作成します。


class JSTFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        return get_jst_timestamp()


def _setup_logger():
    logger = logging.getLogger("DiscordEcoSystem")
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        # コンソール出力用ハンドラ
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)

        # フォーマッタの設定
        formatter = JSTFormatter("[%(asctime)s] [%(levelname)-5s] [%(name)s] %(message)s")
        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)

        # 将来的にファイル出力が必要な場合はここに FileHandler を追加可能
    return logger


_internal_logger = _setup_logger()


class Logger:
    """
    システム全体のログ出力を管理するクラス。
    標準の `logging` モジュールをラップし、既存インターフェースと互換性を保ちます。
    """

    @staticmethod
    def info(module: str, message: str, exc_info=False):
        _internal_logger.getChild(module).info(message, exc_info=exc_info)

    @staticmethod
    def warn(module: str, message: str, exc_info=False):
        _internal_logger.getChild(module).warning(message, exc_info=exc_info)

    @staticmethod
    def error(module: str, message: str, exc_info=False):
        _internal_logger.getChild(module).error(message, exc_info=exc_info)

    @staticmethod
    def debug(module: str, message: str, exc_info=False):
        _internal_logger.getChild(module).debug(message, exc_info=exc_info)
