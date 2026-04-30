from core.utils.exceptions import EconomyError


class InsufficientFundsError(EconomyError):
    """所持金が不足している場合に発生する例外"""

    def __init__(self, message="所持金が不足しています。"):
        super().__init__(message)


class BetLimitViolationError(EconomyError):
    """ベット額がランク上限を超えている場合に発生する例外"""

    pass


class DailyAlreadyClaimedError(EconomyError):
    """既にデイリーボーナスを受け取り済みの場合に発生する例外"""

    pass


class GachaLimitReachedError(EconomyError):
    """本日のガチャ回数上限に達した場合に発生する例外"""

    pass
