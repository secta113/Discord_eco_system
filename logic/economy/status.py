import statistics

from core.economy import wallet


class StatusService:
    """ユーザーの資産ランク、ベンチマーク計算を担当"""

    SYSTEM_ID = 0
    DEFAULT_BENCHMARK = 10000
    ADAPTIVE_THRESHOLD = 10  # 平均値/中央値を切り替える境界人数
    SN_THRESHOLD_RATE = 0.30
    LIMIT_EXEMPT_AMOUNT = 10000
    BET_LIMIT_RATIOS = {"Recovery": 0.15, "Standard": 0.25, "Prime": 0.50}

    @staticmethod
    def get_benchmark() -> float:
        """アクティブユーザー数に応じて、平均値または中央値をベンチマークとして返す"""
        all_balances = wallet.get_all_balances()
        if StatusService.SYSTEM_ID in all_balances:
            del all_balances[StatusService.SYSTEM_ID]

        b_list = list(all_balances.values())
        if not b_list:
            return float(StatusService.DEFAULT_BENCHMARK)

        n = len(b_list)
        if n > StatusService.ADAPTIVE_THRESHOLD:
            # 11人以上なら中央値
            benchmark = statistics.median(b_list)
        else:
            # 10人以下なら平均値
            benchmark = statistics.mean(b_list)

        return max(float(benchmark), 0.0)

    @staticmethod
    def get_median() -> float:
        """互換性のために残すが、基本は get_benchmark を使用する"""
        return StatusService.get_benchmark()

    @staticmethod
    def get_user_status(user_id: int) -> str:
        if user_id == StatusService.SYSTEM_ID:
            return "System"

        benchmark = StatusService.get_benchmark()
        benchmark_int = int(benchmark)
        balance = wallet.load_balance(user_id)

        if balance > benchmark_int:
            return "Prime"
        elif balance >= benchmark * StatusService.SN_THRESHOLD_RATE:
            return "Standard"
        else:
            return "Recovery"

    @staticmethod
    def get_bet_limit(user_id: int) -> int:
        """ユーザーの現在の資産とランクに基づくベット上限額を返す"""
        if user_id == StatusService.SYSTEM_ID:
            return 999_999_999_999  # 無制限

        balance = wallet.load_balance(user_id)
        status = StatusService.get_user_status(user_id)
        ratio = StatusService.BET_LIMIT_RATIOS.get(status, 0.25)

        return int(balance * ratio)
