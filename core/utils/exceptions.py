class BotError(Exception):
    """ボット内の共通例外クラス。ユーザー向けのメッセージを保持します。"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class EconomyError(BotError):
    """経済的なロジック（残高不足、デイリー処理等）に関するエラー。"""

    pass


class DataValidationError(BotError):
    """データの型や形式の検証に関するエラー。"""

    pass


class MaintenanceError(BotError):
    """メンテナンスモード中にコマンドが実行された際のエラー。"""

    pass


class GameError(BotError):
    """ゲーム進行中（期限切れ、不正なアクション等）のエラー。"""

    pass


class StorageError(BotError):
    """データベース等の保存・読み込み処理に関するエラー。"""

    pass
