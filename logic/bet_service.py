from core.utils.logger import Logger
from logic.constants import GameType, JPRarity

from .economy.bonus import BonusService
from .economy.eco_exceptions import BetLimitViolationError, DailyAlreadyClaimedError
from .economy.jackpot import JackpotService
from .economy.provider import EconomyProvider
from .economy.status import StatusService


class BetService:
    """
    ファサード層: 外部（ゲーム等）からの経済ルール呼び出し窓口。
    実体は logic/economy/ 配下の各専門サービスに委譲。
    """

    SYSTEM_ID = StatusService.SYSTEM_ID
    SYSTEM_JACKPOT_ID = JackpotService.SYSTEM_JACKPOT_ID

    # マッチボーナス設定（EconomyProviderに持たせても良いが、窓口で管理）
    MATCH_BONUS_RATE = 0.05
    RUBBERBAND_MULTIPLIER = 1.5

    @staticmethod
    def get_user_status(user_id: int) -> str:
        return StatusService.get_user_status(user_id)

    @staticmethod
    def get_median() -> float:
        return StatusService.get_median()

    @staticmethod
    def escrow(user_id: int, amount: int, reason: str = "参加コスト") -> bool:
        return EconomyProvider.escrow(user_id, amount, reason)

    @staticmethod
    def payout(
        user_id: int, amount: int, is_pvp: bool = False, reason: str = "配当ポイント"
    ) -> int:
        """
        払い出しを行う。
        is_pvp が True の場合、対人戦のシステムレバレッジ（ボーナス）を上乗せして支払う。
        Challenger/Distressed にはラバーバンド効果（1.5倍）を適用。
        """
        bonus_rate = 0.0
        if is_pvp:
            bonus_rate = BetService.MATCH_BONUS_RATE
            status = StatusService.get_user_status(user_id)
            if status in ["Standard", "Recovery"]:
                bonus_rate *= BetService.RUBBERBAND_MULTIPLIER

        return EconomyProvider.payout(user_id, amount, bonus_rate=bonus_rate, reason=reason)

    @staticmethod
    def split_payout(
        user_ids: list, total_pot: int, is_pvp: bool = False, reason: str = "ゲーム勝利配当"
    ) -> int:
        # Payout関数をラップして渡す
        def wrapper(uid, amt, reason):
            return BetService.payout(uid, amt, is_pvp=is_pvp, reason=reason)

        return EconomyProvider.split_payout(user_ids, total_pot, wrapper, reason)

    @staticmethod
    def add_to_jackpot(amount: int):
        JackpotService.add_to_jackpot(amount)

    @staticmethod
    def add_to_jackpot_real_only(
        amount: int, total_pot: int, real_pot: int, module: str = "Economy"
    ) -> int:
        """
        仮想マネー（NPC等の賭け金）を除いた、実際の入金額の比率分のみをジャックポットへ回収する。
        """
        if total_pot <= 0 or real_pot <= 0:
            return 0

        # 実入金比率を算出 (例: Pot 300のうち人間が100なら 1/3)
        ratio = min(1.0, real_pot / total_pot)
        collectible = int(amount * ratio)

        if collectible > 0:
            JackpotService.add_to_jackpot(collectible)
            Logger.info(
                module,
                f"Inflation Protection: Collected {collectible} pts (Target: {amount}, Ratio: {ratio:.2f})",
            )
        else:
            Logger.debug(
                module, f"Inflation Protection: No real portion to collect (Ratio: {ratio:.2f})"
            )

        return collectible

    @staticmethod
    def execute_jackpot(user_id: int, game_type: GameType, rarity: JPRarity, hand_name: str) -> int:
        """
        指定されたレアリティに基づきジャックポットを放出する。
        """

        # Payout関数をラップして渡す（JP放出時はPvPボーナス対象外）
        def wrapper(uid, amt, reason):
            return BetService.payout(uid, amt, is_pvp=False, reason=reason)

        return JackpotService.execute_jackpot(user_id, game_type, rarity, hand_name, wrapper)

    @staticmethod
    def claim_daily(user_id: int, force: bool = False) -> str:
        """デイリーボーナスを請求する。既に受け取り済みの場合は例外を送出。"""
        success, msg = BonusService.claim_daily(user_id, force=force)
        if not success:
            raise DailyAlreadyClaimedError(msg)
        return msg

    @staticmethod
    def validate_bet(user_id: int, amount: int) -> bool:
        """ベット額がユーザーのランクに基づく上限以内か検証する。上限超えの場合は例外を送出。"""
        if amount <= StatusService.LIMIT_EXEMPT_AMOUNT:
            return True

        limit = StatusService.get_bet_limit(user_id)
        if amount > limit:
            status = StatusService.get_user_status(user_id)
            Logger.warn(
                "Economy",
                f"Bet Limit Violation: user:{user_id} rank:{status} bet:{amount} limit:{limit}",
            )
            ratio_pct = int(StatusService.BET_LIMIT_RATIOS.get(status, 0.25) * 100)

            raise BetLimitViolationError(
                f"❌ ベット額が上限を超えています。現在のランク（{status}）では資産の {ratio_pct}% ({limit} pts) までベット可能です。"
            )
        return True
