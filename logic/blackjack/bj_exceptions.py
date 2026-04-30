from core.utils.exceptions import GameError


class BlackjackError(GameError):
    """ブラックジャックに関連する全ての例外の基底クラス"""

    pass


class BlackjackTurnError(BlackjackError):
    """自分の手番ではない場合に発生する例外"""

    def __init__(self, message="今はあなたの番ではありません。"):
        super().__init__(message)


class BlackjackActionError(BlackjackError):
    """不正なアクション（条件外のダブルダウンなど）が選択された場合に発生する例外"""

    pass


class BlackjackInsufficientFundsError(BlackjackError):
    """所持金が不足している場合に発生する例外"""

    pass
