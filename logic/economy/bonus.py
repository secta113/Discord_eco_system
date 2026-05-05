import datetime

from core.economy import wallet
from core.utils.formatters import f_commas, f_pts
from core.utils.logger import Logger

from .jackpot import JackpotService
from .status import StatusService


class BonusService:
    """デイリーボーナスのロジックを担当 (v2.4)"""

    BI_RATE = 0.05
    SN_DIFF_RATE = 0.50
    DIVIDEND_RATE = 0.01
    DAILY_BASE_PAY = 1000

    @staticmethod
    def claim_daily(user_id: int, force: bool = False) -> tuple[bool, str]:
        jst_now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
        today_str = jst_now.strftime("%Y-%m-%d")

        balance = wallet.load_balance(user_id)
        last_daily = wallet.get_last_daily(user_id)

        if not force and last_daily == today_str:
            return False, "本日のデイリーボーナスは既に受け取り済みです。"

        # システムアカウント(ID: 0)への自動連動ロジック
        if user_id != StatusService.SYSTEM_ID:
            last_system_daily = wallet.get_last_daily(StatusService.SYSTEM_ID)
            if last_system_daily != today_str:
                # システム分も未請求なら実行 (再帰呼び出しだが、ID=0なのでこのブロックはスキップされる)
                BonusService.claim_daily(StatusService.SYSTEM_ID)

        benchmark = StatusService.get_benchmark()
        status = StatusService.get_user_status(user_id)

        # 1. 基本給
        total_bonus = BonusService.DAILY_BASE_PAY
        tier_bonus = 0

        # 2. ティア別ボーナス
        sn_threshold = benchmark * StatusService.SN_THRESHOLD_RATE

        if status == "Prime":
            # 資産配当: MAX(残高1%, 基準額5%)
            tier_bonus = int(
                max(balance * BonusService.DIVIDEND_RATE, benchmark * BonusService.BI_RATE)
            )
        elif status == "Standard":
            # 底上げ配当: 基準額5%
            tier_bonus = int(benchmark * BonusService.BI_RATE)
        elif status == "Recovery":
            # 復興支援: (基準額5%) + (差分50%)
            bi_comp = benchmark * BonusService.BI_RATE
            sn_comp = (sn_threshold - balance) * BonusService.SN_DIFF_RATE
            tier_bonus = int(bi_comp + sn_comp)
        elif status == "System":
            # システム(JPプール): Standardと同等の底上げ配当
            tier_bonus = int(benchmark * BonusService.BI_RATE)

        total_bonus += tier_bonus

        # 3. 特別給付 (JOD: ジャックポット・オーバーフロー配当)
        overflow_dividend = 0
        if user_id != StatusService.SYSTEM_ID:
            overflow_dividend = JackpotService.claim_overflow_dividend(user_id, status)
            total_bonus += overflow_dividend

        # 支給処理
        wallet.save_balance(user_id, balance + total_bonus)
        wallet.set_last_daily(user_id, today_str)
        wallet.add_history(user_id, "デイリーボーナス", total_bonus)

        # 監査ログの強化: 支給額の内訳を詳細に記録
        Logger.info(
            "Bonus",
            f"DAILY_CLAIM: user:{user_id} status:{status} total:{total_bonus} "
            f"(Base:{BonusService.DAILY_BASE_PAY}, Tier:{tier_bonus}, JOD:{overflow_dividend}) "
            f"Bench:{benchmark:.0f}",
        )

        status_msg = f"ステータス: {status}"
        if status == "Recovery":
            status_msg += " (復興支援適用)"
        elif status == "Prime":
            status_msg += " (資産配当適用)"

        dividend_msg = ""
        if overflow_dividend > 0:
            dividend_msg = f"\n💰 特別給付(JP還元): {f_pts(overflow_dividend, signed=True)}"

        return (
            True,
            f"デイリーボーナス {f_pts(total_bonus)} を支給しました！{dividend_msg}\n({status_msg} / ベンチマーク: {f_pts(benchmark)})",
        )
