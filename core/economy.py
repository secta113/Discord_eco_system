from typing import Dict, List, Optional, Union

from core.handlers.storage import (
    ISystemRepository,
    IUserRepository,
    SQLiteSystemRepository,
    SQLiteUserRepository,
)
from core.models.validation import UserSchema
from core.utils.time_utils import get_jst_timestamp


class WalletManager:
    """
    データアクセス層: 永続化を担当。
    User形態のリポジトリとSystem形態のリポジトリを利用してデータを管理します。
    """

    def __init__(self, user_repo: IUserRepository, system_repo: ISystemRepository):
        self.user_repo = user_repo
        self.system_repo = system_repo
        self.INITIAL_BALANCE = 10000

    def _get_user_model(self, user_id: int) -> UserSchema:
        """
        ユーザーモデルを取得する。存在しない場合は初期化モデルを作成する。
        システムアカウント(ID=0)の場合は、専用ストレージからプロキシデータを作成して返す。
        """
        if user_id == 0:
            sys_data = self.system_repo.get_system_data("jackpot_pool") or {}
            return UserSchema(
                id=0,
                balance=sys_data.get("balance", 0),
                last_daily=sys_data.get("last_daily", "1970-01-01"),
                last_gacha_daily="1970-01-01",
                gacha_collection=[],
                history=[],
                total_wins=0,
                games_played=0,
                max_win_amount=0,
                gacha_count_today=0,
                last_wild_battle_date=sys_data.get("last_wild_battle_date", "1970-01-01"),
                wild_battle_count_today=sys_data.get("wild_battle_count_today", 0),
            )

        user = self.user_repo.get_user(user_id)
        if user is None:
            user = UserSchema(
                id=user_id,
                balance=self.INITIAL_BALANCE,
                last_daily="1970-01-01",
                last_gacha_daily="1970-01-01",
                gacha_collection=[],
                history=[],
                total_wins=0,
                games_played=0,
                max_win_amount=0,
                gacha_count_today=0,
                last_wild_battle_date="1970-01-01",
                wild_battle_count_today=0,
            )
            self.user_repo.save_user(user)
        return user

    def _save_user_model(self, user_id: int, user: UserSchema):
        """
        ユーザーモデルを保存する。
        システムアカウント(ID=0)の場合は、専用ストレージ側の該当項目のみを更新する。
        """
        if user_id == 0:
            self.system_repo.save_system_data(
                "jackpot_pool",
                {
                    "balance": user.balance,
                    "last_daily": user.last_daily,
                    "last_wild_battle_date": user.last_wild_battle_date,
                    "wild_battle_count_today": user.wild_battle_count_today,
                },
            )
        else:
            self.user_repo.save_user(user)

    def load_balance(self, user_id: int) -> int:
        user = self._get_user_model(user_id)
        return user.balance

    def save_balance(self, user_id: int, balance: int):
        user = self._get_user_model(user_id)
        user.balance = balance
        self._save_user_model(user_id, user)

    def get_last_daily(self, user_id: int) -> str:
        return self._get_user_model(user_id).last_daily

    def set_last_daily(self, user_id: int, date_str: str):
        user = self._get_user_model(user_id)
        user.last_daily = date_str
        self._save_user_model(user_id, user)

    def get_last_gacha_daily(self, user_id: int) -> str:
        return self._get_user_model(user_id).last_gacha_daily

    def set_last_gacha_daily(self, user_id: int, date_str: str):
        user = self._get_user_model(user_id)
        user.last_gacha_daily = date_str
        self._save_user_model(user_id, user)

    def get_gacha_collection(self, user_id: int) -> List[int]:
        return self._get_user_model(user_id).gacha_collection

    def add_to_gacha_collection(self, user_id: int, event_id: int):
        user = self._get_user_model(user_id)
        if event_id not in user.gacha_collection:
            user.gacha_collection.append(event_id)
            self._save_user_model(user_id, user)

    def get_gacha_count(self, user_id: int) -> int:
        return self._get_user_model(user_id).gacha_count_today

    def set_gacha_count(self, user_id: int, count: int):
        user = self._get_user_model(user_id)
        user.gacha_count_today = count
        self._save_user_model(user_id, user)

    def get_last_wild_battle_date(self, user_id: int) -> str:
        return self._get_user_model(user_id).last_wild_battle_date

    def set_last_wild_battle_date(self, user_id: int, date_str: str):
        user = self._get_user_model(user_id)
        user.last_wild_battle_date = date_str
        self._save_user_model(user_id, user)

    def get_wild_battle_count(self, user_id: int) -> int:
        return self._get_user_model(user_id).wild_battle_count_today

    def set_wild_battle_count(self, user_id: int, count: int):
        user = self._get_user_model(user_id)
        user.wild_battle_count_today = count
        self._save_user_model(user_id, user)

    def get_all_balances(self) -> Dict[int, int]:
        all_users = self.user_repo.get_all_users()
        return {uid: user.balance for uid, user in all_users.items()}

    def get_all_stats(self) -> Dict[int, UserSchema]:
        """全ユーザーの全データを返す"""
        return self.user_repo.get_all_users()

    def add_history(self, user_id: int, reason: str, amount: int):
        if user_id <= 0:
            return  # NPCやシステムは履歴を保存しない

        user = self._get_user_model(user_id)
        now_str = get_jst_timestamp()
        record = {"date": now_str, "reason": reason, "amount": amount}
        user.history.append(record)

        # 履歴は直近20件のみ保持
        if len(user.history) > 20:
            user.history = user.history[-20:]

        self._save_user_model(user_id, user)

    def get_history(self, user_id: int) -> List[Dict]:
        return self._get_user_model(user_id).history

    def update_stats(self, user_id: int, is_win: bool = False, amount_won: int = 0):
        user = self._get_user_model(user_id)

        # 参加回数をインクリメント
        user.games_played += 1

        if is_win:
            user.total_wins += 1
            if amount_won > user.max_win_amount:
                user.max_win_amount = amount_won

        self._save_user_model(user_id, user)

    def get_stats(self, user_id: int) -> Dict[str, int]:
        user = self._get_user_model(user_id)
        return {
            "total_wins": user.total_wins,
            "games_played": user.games_played,
            "max_win_amount": user.max_win_amount,
        }


# 個別のリポジトリを注入
wallet = WalletManager(SQLiteUserRepository(), SQLiteSystemRepository())
