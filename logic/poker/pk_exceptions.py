from core.utils.exceptions import GameError


class PokerError(GameError):
    """ポーカーに関連する全ての例外の基底クラス"""

    pass


class PokerTurnError(PokerError):
    """自分の手番ではない場合に発生する例外"""

    def __init__(self, message="あなたの手番ではありません。"):
        super().__init__(message)


class PokerActionError(PokerError):
    """不正なアクション（レイズ額不足など）が選択された場合に発生する例外"""

    pass


class PokerStateError(PokerError):
    """ゲームの状態が不正な場合（既に終了しているなど）に発生する例外"""

    pass


class PokerInsufficientStackError(PokerError):
    """スタックが不足している場合に発生する例外"""

    def __init__(self, required: int, current: int, context: str = ""):
        self.required = required
        self.current = current
        msg = f"スタックが不足しています。 (必要: {required:,} pts, 現在: {current:,} pts)"
        if context:
            msg += f"\n{context}"
        super().__init__(msg)
