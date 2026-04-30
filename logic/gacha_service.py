import datetime
import json
import os
import random

from core.economy import wallet
from core.utils.logger import Logger
from logic.bet_service import BetService
from logic.economy.eco_exceptions import GachaLimitReachedError, InsufficientFundsError


class GachaService:
    GACHA_COST = 500
    PAYOUT_MAP = {
        "Ultimate": 0,
        "Legendary": 15000,
        "Epic": 4000,
        "Rare": 2000,
        "Normal": 1000,
        "Bad": 400,
        "Disaster": 0,
    }

    def __init__(self, json_path: str = None):
        if json_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.json_path = os.path.join(base_dir, "data", "gacha_event.json")
        else:
            self.json_path = json_path

        self.events = []
        self._load_events()

    def get_current_cost(self, user_id: int) -> int:
        """現在の回数に応じたコストを返す (500, 1000, 1500)"""
        self._check_and_reset_daily(user_id)
        count = wallet.get_gacha_count(user_id)
        if count == 0:
            return 500
        if count == 1:
            return 1000
        return 1500

    def _check_and_reset_daily(self, user_id: int):
        """日付が変わっていたら回数をリセットする"""
        jst_now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
        today_str = jst_now.strftime("%Y-%m-%d")
        last_gacha = wallet.get_last_gacha_daily(user_id)

        if last_gacha != today_str:
            wallet.set_gacha_count(user_id, 0)
            # last_gacha_daily 自体は実行時に更新されるが、リセット判定のために保持

    def _load_events(self):
        """JSONからイベントデータをロードしてキャッシュする"""
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                self.events = json.load(f)
            Logger.info("Gacha", f"Loaded {len(self.events)} events from {self.json_path}")
        except Exception as e:
            Logger.error("Gacha", f"Error loading events: {e}")
            self.events = []

    def get_completion_info(self, user_id: int) -> tuple[int, int, float]:
        """コンプリート数、総数、パーセンテージを返す"""
        if not self.events:
            return 0, 0, 0.0

        collection = wallet.get_gacha_collection(user_id)
        total = len(self.events)
        collected = len([eid for eid in collection if any(e["id"] == eid for e in self.events)])
        percentage = (collected / total * 100) if total > 0 else 0.0
        return collected, total, percentage

    def can_play(self, user_id: int):
        """ガチャが実行可能かチェックする (1日3回制限)。不可の場合は例外を送出。"""
        self._check_and_reset_daily(user_id)
        count = wallet.get_gacha_count(user_id)

        if count >= 3:
            raise GachaLimitReachedError(
                "本日のガチャ上限（3回）に達しました。明日また運試ししましょう！"
            )

        cost = self.get_current_cost(user_id)
        balance = wallet.load_balance(user_id)
        if balance < cost:
            raise InsufficientFundsError(
                f"所持金が不足しています。今回のガチャには {cost} pts 必要です。"
            )

    def execute_gacha(self, user_id: int) -> dict:
        """ガチャを実行し、結果を返す。失敗（上限や資金不足）時は例外を送出。"""
        self.can_play(user_id)

        if not self.events:
            from core.utils.exceptions import BotError

            raise BotError("ガチャデータが読み込めませんでした。管理者に連絡してください。")

        cost = self.get_current_cost(user_id)
        count = wallet.get_gacha_count(user_id)
        collection = wallet.get_gacha_collection(user_id)

        # 1. 支払い
        BetService.escrow(user_id, cost, reason=f"ガチャ実行コスト ({count + 1}回目)")

        # 2. 抽選
        # 初回かつ未コンプなら新規確定モード
        candidates = self.events
        is_guaranteed_new = False
        if count == 0:
            uncollected = [e for e in self.events if e["id"] not in collection]
            if uncollected:
                candidates = uncollected
                is_guaranteed_new = True

        event = random.choice(candidates)
        rarity = event.get("rarity", "Normal")
        payout = self.PAYOUT_MAP.get(rarity, 0)

        # 3. 配当
        BetService.payout(user_id, payout, reason=f"ガチャ配当 [{rarity}]")

        # 4. 図鑑記録 (新規獲得判定)
        is_new = event["id"] not in collection
        wallet.add_to_gacha_collection(user_id, event["id"])

        # 5. 実行記録更新
        jst_now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
        wallet.set_last_gacha_daily(user_id, jst_now.strftime("%Y-%m-%d"))
        wallet.set_gacha_count(user_id, count + 1)

        result = {
            "event": event,
            "payout": payout,
            "cost": cost,
            "is_new": is_new,
            "is_guaranteed_new": is_guaranteed_new,
            "count_today": count + 1,
        }

        return result


# Singleton instance
gacha_service = GachaService()
