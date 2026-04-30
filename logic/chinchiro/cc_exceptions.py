from core.utils.exceptions import GameError


class ChinchiroError(GameError):
    """チンチロリンに関連する全ての例外の基底クラス"""

    pass


class ChinchiroTurnError(ChinchiroError):
    """自分の手番ではない場合に発生する例外"""

    def __init__(self, current_player_mention: str):
        super().__init__(f"今は {current_player_mention} の番です。")


class ChinchiroStateError(ChinchiroError):
    """ゲームの状態が不正な場合に発生する例外"""

    pass
