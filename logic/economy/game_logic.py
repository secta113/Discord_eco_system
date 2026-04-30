from typing import Optional

from logic.bet_service import BetService


class GameLogicService:
    """
    ゲーム全般に共通するロジック（接待レート等）を管理 (v2.4)。
    """

    HOSPITALITY_RATES = {"Prime": 0.05, "Standard": 0.20, "Recovery": 0.40}

    @staticmethod
    def get_hospitality_rate(user_id: int, status_rank: Optional[str] = None) -> float:
        """ユーザーのステータスに応じた接待率を返す"""
        if status_rank is None:
            status_rank = BetService.get_user_status(user_id)
        return GameLogicService.HOSPITALITY_RATES.get(status_rank, 0.05)
