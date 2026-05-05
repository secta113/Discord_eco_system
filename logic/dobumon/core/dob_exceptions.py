from core.utils.exceptions import GameError


class DobumonError(GameError):
    """怒武者（ドブモン）関連の基底例外クラス"""

    def __init__(self, message: str):
        super().__init__(message)


class DobumonNotFoundError(DobumonError):
    """対象の怒武者が見つからない場合のエラー"""

    def __init__(self, message: str = "対象の怒武者が存在しないか、既に生存していません。"):
        super().__init__(message)


class DobumonInsufficientPointsError(DobumonError):
    """ポイント不足によるエラー"""

    def __init__(self, required: int, current: int, context: str = ""):
        msg = f"ポイントが足りません。 (必要: {required:,} pts, 現在: {current:,} pts)"
        if context:
            msg += f"\n{context}"
        super().__init__(msg)


class DobumonStatusError(DobumonError):
    """個体の状態（死亡、病気、属性等）による制限エラー"""

    pass


class DobumonGeneticsError(DobumonError):
    """遺伝子操作や突然変異に関するロジックエラー"""

    pass


class DobumonExecutionError(DobumonError):
    """アクションの実行自体に失敗した場合のエラー"""

    pass
