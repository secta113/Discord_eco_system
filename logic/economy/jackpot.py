import json
import os
import threading
import time

from core.economy import wallet
from core.utils.constants import GameType, JPRarity
from core.utils.logger import Logger


class JackpotService:
    """
    ジャックポットプールの管理を担当 (v2.11)
    レアリティに基づいた配当計算、セーフティ・キャップの適用、および監査ログの記録を行う。
    """

    SYSTEM_JACKPOT_ID = 0

    # TC キャッシュ用
    _tc_cache = None
    _tc_cache_time = 0
    _tc_lock = threading.Lock()
    TC_CACHE_TTL = 60  # 60秒キャッシュ

    # レアリティごとのプール放出率
    PAYOUT_RATES = {
        JPRarity.LEGENDARY: 1.0,  # 100%
        JPRarity.EPIC: 0.3,  # 30%
        JPRarity.RARE: 0.1,  # 10%
        JPRarity.COMMON: 0.03,  # 3%
    }

    # ゲームごとのプール放出比率上限 (Ratio Cap)
    GAME_RATIO_CAPS = {
        GameType.POKER: 1.0,
        GameType.BLACKJACK: 0.5,
        GameType.CHINCHIRO: 0.2,
    }

    # 総流通量(Total Circulation)に対する放出上限比率 (Dynamic Hard Cap)
    DYNAMIC_HARD_CAP_RATIOS = {
        JPRarity.LEGENDARY: 0.5,  # 50%
        JPRarity.EPIC: 0.15,  # 15%
        JPRarity.RARE: 0.05,  # 5%
        JPRarity.COMMON: 0.02,  # 2%
    }

    # 総流通量(Total Circulation)に対する最低保証比率 (Dynamic Min Payout)
    DYNAMIC_MIN_PAYOUT_RATIOS = {
        JPRarity.LEGENDARY: 0.02,
        JPRarity.EPIC: 0.005,
        JPRarity.RARE: 0.001,
        JPRarity.COMMON: 0.0002,
    }

    # JOD (Jackpot Overflow Dividend) 設定
    OVERFLOW_THRESHOLD_RATIO = 3.0
    OVERFLOW_DIVIDEND_RATE = 0.01
    OVERFLOW_RANK_MULTIPLIERS = {
        "Recovery": 2.0,
        "Standard": 1.0,
        "Prime": 0.5,
    }

    @staticmethod
    def load_config():
        """外部設定ファイルから定数を読み込む (v2.5)"""
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        if not os.path.exists(config_path):
            Logger.warning("Jackpot", f"Config file not found: {config_path}")
            return

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            # レアリティベースの定数マッピング
            rarity_maps = {
                "PAYOUT_RATES": "PAYOUT_RATES",
                "DYNAMIC_HARD_CAP_RATIOS": "DYNAMIC_HARD_CAP_RATIOS",
                "DYNAMIC_MIN_PAYOUT_RATIOS": "DYNAMIC_MIN_PAYOUT_RATIOS",
            }
            for json_key, attr_name in rarity_maps.items():
                if json_key in config:
                    setattr(
                        JackpotService,
                        attr_name,
                        {
                            JPRarity[k]: v
                            for k, v in config[json_key].items()
                            if k in JPRarity.__members__
                        },
                    )

            # ゲーム種別ベースの定数マッピング
            if "GAME_RATIO_CAPS" in config:
                JackpotService.GAME_RATIO_CAPS = {
                    GameType[k]: v
                    for k, v in config["GAME_RATIO_CAPS"].items()
                    if k in GameType.__members__
                }

            # JOD 設定の読み込み
            if "OVERFLOW_THRESHOLD_RATIO" in config:
                JackpotService.OVERFLOW_THRESHOLD_RATIO = float(config["OVERFLOW_THRESHOLD_RATIO"])
            if "OVERFLOW_DIVIDEND_RATE" in config:
                JackpotService.OVERFLOW_DIVIDEND_RATE = float(config["OVERFLOW_DIVIDEND_RATE"])
            if "OVERFLOW_RANK_MULTIPLIERS" in config:
                JackpotService.OVERFLOW_RANK_MULTIPLIERS = config["OVERFLOW_RANK_MULTIPLIERS"]

            Logger.info("Jackpot", "Economy config loaded from config.json")
        except Exception as e:
            Logger.error("Jackpot", f"Failed to load config.json: {e}")

    @staticmethod
    def get_total_circulation() -> int:
        """システム口座以外の全ユーザーの残高合計を算出する (キャッシュ付き/スレッドセーフ)"""
        with JackpotService._tc_lock:
            now = time.time()
            if (
                JackpotService._tc_cache is not None
                and (now - JackpotService._tc_cache_time) < JackpotService.TC_CACHE_TTL
            ):
                return JackpotService._tc_cache

            all_balances = wallet.get_all_balances()
            # ID 0 は既にもう get_all_balances で除外されているが、念のためフィルタリング
            total = sum(bal for uid, bal in all_balances.items() if int(uid) > 0)

            JackpotService._tc_cache = max(total, 1)  # ゼロ除算防止
            JackpotService._tc_cache_time = now
            return JackpotService._tc_cache

    @staticmethod
    def _load_pool() -> int:
        """システムプール残高を専用ストレージから取得する"""
        return wallet.load_balance(JackpotService.SYSTEM_JACKPOT_ID)

    @staticmethod
    def _save_pool(balance: int):
        """システムプール残高を専用ストレージに保存する"""
        wallet.save_balance(JackpotService.SYSTEM_JACKPOT_ID, balance)

    @staticmethod
    def get_pool_balance() -> int:
        """現在のシステムプール残高を取得する (公開メソッド)"""
        return JackpotService._load_pool()

    @staticmethod
    def add_to_jackpot(amount: int):
        """システムプールに徴収分を追加する"""
        current = JackpotService._load_pool()
        new_pool = current + amount
        JackpotService._save_pool(new_pool)

        Logger.info("Economy", f"Jackpot Pool Collection: +{amount} pts. New Pool: {new_pool}")

    @staticmethod
    def calculate_payout(game_type: GameType, rarity: JPRarity) -> int:
        """
        現在のプール、レアリティ、および総流通量に基づき、動的に配当額を算出する。
        三重制約:
        1. 物理配当 (Pool * Rate) を、ゲームごとの比率制限 (Pool * GameCap) で絞る。
        2. 総流通量に対するハードキャップを適用。
        3. 総流通量に対する最低保証を適用。
        """
        if rarity == JPRarity.NONE:
            return 0

        pool = JackpotService._load_pool()
        tc = JackpotService.get_total_circulation()

        # 1. 暫定物理配当 (ゲーム比率制限適用)
        rate = JackpotService.PAYOUT_RATES.get(rarity, 0)
        game_cap_ratio = JackpotService.GAME_RATIO_CAPS.get(game_type, 1.0)
        raw_payout = int(pool * min(rate, game_cap_ratio))

        # 2. 動的上限制約 (総流通量比)
        hard_cap_ratio = JackpotService.DYNAMIC_HARD_CAP_RATIOS.get(rarity, 1.0)
        capped_payout = min(raw_payout, int(tc * hard_cap_ratio))

        # 3. 動的下限適用 (最低保証)
        min_payout_ratio = JackpotService.DYNAMIC_MIN_PAYOUT_RATIOS.get(rarity, 0)
        final_payout = max(capped_payout, int(tc * min_payout_ratio))

        return final_payout

    @staticmethod
    def execute_jackpot(
        user_id: int, game_type: GameType, rarity: JPRarity, hand_name: str, payout_func
    ) -> int:
        """
        ジャックポット放出を実行し、ログに記録する。不足分はシステムが補填する。
        """
        if rarity == JPRarity.NONE:
            return 0

        payout_amount = JackpotService.calculate_payout(game_type, rarity)

        if payout_amount > 0:
            pool_before = JackpotService._load_pool()

            # プールからの支出（不足時はプール全額を放出して0にする）
            actual_from_pool = min(pool_before, payout_amount)
            pool_after = pool_before - actual_from_pool
            JackpotService._save_pool(pool_after)

            compensation = payout_amount - actual_from_pool
            if compensation > 0:
                Logger.info(
                    "Jackpot", f"System compensated {compensation} pts for rarity {rarity.name}"
                )

            # 実際の支払いは外部の配当関数（BetService経由）に委譲
            payout_func(
                user_id,
                payout_amount,
                reason=f"ジャックポット配当 ({game_type.value}: {hand_name})",
            )

            # 監査ログの記録
            wallet.system_repo.log_jackpot(
                user_id=user_id,
                game_type=game_type.value,
                hand_name=hand_name,
                rarity=rarity.name,
                amount=payout_amount,
                pool_after=pool_after,
            )

            Logger.info(
                "Jackpot",
                f"RELEASE: user:{user_id} game:{game_type.value} rarity:{rarity.name} amount:{payout_amount} pool_after:{pool_after}",
            )

        return payout_amount

    @staticmethod
    def claim_overflow_dividend(user_id: int, user_status: str) -> int:
        """
        プールが肥大化している場合に、余剰分の一部を配当としてプレイヤーに還元する。
        """
        pool = JackpotService.get_pool_balance()
        tc = JackpotService.get_total_circulation()

        # 閾値チェック
        threshold = int(tc * JackpotService.OVERFLOW_THRESHOLD_RATIO)
        overflow = pool - threshold

        if overflow <= 0:
            return 0

        # 配当額の計算
        base_dividend = overflow * JackpotService.OVERFLOW_DIVIDEND_RATE
        multiplier = JackpotService.OVERFLOW_RANK_MULTIPLIERS.get(user_status, 1.0)
        final_dividend = int(base_dividend * multiplier)

        if final_dividend <= 0:
            return 0

        # プールから差し引き (不足時はプール全額)
        actual_payout = min(pool, final_dividend)
        JackpotService._save_pool(pool - actual_payout)

        Logger.info(
            "Jackpot",
            f"JOD_RELEASE: user:{user_id} status:{user_status} amount:{actual_payout} (Overflow:{overflow})",
        )

        return actual_payout


# 初期化時に設定を読み込む
JackpotService.load_config()
