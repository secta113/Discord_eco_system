import math

from core.economy import wallet
from core.utils.logger import Logger

from .eco_exceptions import InsufficientFundsError


class EconomyProvider:
    """基礎的な入出金、エスクローを担当"""

    @staticmethod
    def escrow(user_id: int, amount: int, reason: str = "参加コスト") -> bool:
        current = wallet.load_balance(user_id)
        if current < amount:
            raise InsufficientFundsError()
        wallet.save_balance(user_id, current - amount)
        if amount > 0:
            wallet.add_history(user_id, reason, -amount)
            Logger.info("Economy", f"user:{user_id} amount:-{amount} reason:{reason}")
        return True

    @staticmethod
    def payout(
        user_id: int, amount: int, bonus_rate: float = 0.0, reason: str = "配当ポイント"
    ) -> int:
        """払い出しを実行。ボーナス率が指定されている場合は加算。"""
        # 誤差対策として切り上げを採用
        bonus_amount = math.ceil(amount * bonus_rate)
        final_amount = amount + bonus_amount

        current = wallet.load_balance(user_id)
        wallet.save_balance(user_id, current + final_amount)
        if final_amount > 0:
            wallet.add_history(user_id, reason, final_amount)
            Logger.info("Economy", f"user:{user_id} amount:{final_amount} reason:{reason}")
        return final_amount

    @staticmethod
    def split_payout(
        user_ids: list, total_pot: int, payout_func, reason: str = "ゲーム勝利配当"
    ) -> int:
        """均等割り。payout_func は (uid, amount) を受け取る関数。"""
        if not user_ids:
            return 0
        payout_per_person = total_pot // len(user_ids)
        actual_payout = 0
        for uid in user_ids:
            actual_payout = payout_func(uid, payout_per_person, reason=reason)
        return actual_payout
