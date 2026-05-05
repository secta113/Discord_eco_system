from logic.bet_service import BetService
from managers.game_session import BaseGameSession


class MatchService(BaseGameSession):
    """
    アプリケーション層: 外部ゲーム用エスクロー（仕様書4.0）
    """

    def __init__(self, channel_id, bet_amount, host_user=None):
        super().__init__(channel_id, bet_amount)
        # host_id は BaseGameSession のプロパティで players[0]['id'] を返すが、
        # 明示的に保存しておきたい場合はフィールドとしても持てる。
        # ここでは Base の仕組みに乗る。

    @property
    def game_type(self) -> str:
        return "match"

    @property
    def game_name(self) -> str:
        return "外部マッチ"

    @property
    def min_players(self) -> int:
        return 2

    def settle(self, winner_ids: list):
        """勝者に山分け配当"""
        is_pvp = len(self.players) >= 2
        payout_per_person = BetService.split_payout(
            winner_ids, self.pot, is_pvp=is_pvp, reason=f"外部マッチ 配当 (Entry {self.bet_amount})"
        )
        self.status = "settled"

        from core.economy import wallet
        # from core.utils.exceptions import BotError  # 未使用のため削除
        # from core.utils.logger import Logger       # 未使用のため削除

        for p in self.players:
            uid = p["id"]
            if uid > 0:
                is_win = uid in winner_ids
                wallet.update_stats(
                    uid, is_win=is_win, amount_won=payout_per_person if is_win else 0
                )

        return payout_per_person

    def cancel(self):
        """返金処理 (BaseGameSession.refund_all と等価だが、エイリアスとして残す)"""
        self.refund_all()
