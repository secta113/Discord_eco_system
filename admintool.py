import argparse
import os
import sys

# プロジェクトルートをパスに追加 (coreパッケージをインポートするため)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.economy import wallet
from core.utils.logger import Logger
from logic.bet_service import BetService


def handle_give(args):
    current = wallet.load_balance(args.user_id)
    wallet.save_balance(args.user_id, current + args.amount)
    wallet.add_history(args.user_id, args.reason, args.amount)
    Logger.info(
        "Admin",
        f"DONE: {args.user_id} に {args.amount} pts 付与しました。(新残高: {current + args.amount} pts)",
    )


def handle_remove(args):
    current = wallet.load_balance(args.user_id)
    if current < args.amount:
        Logger.error("Admin", f"残高不足です (現在の残高: {current} pts)")
        return

    # BetService.escrow を使用して一貫性を保つ
    if BetService.escrow(args.user_id, args.amount, reason=args.reason):
        Logger.info(
            "Admin",
            f"DONE: {args.user_id} から {args.amount} pts 回収しました。(新残高: {current - args.amount} pts)",
        )
    else:
        Logger.error("Admin", "回収に失敗しました。")


def handle_transfer(args):
    from_bal = wallet.load_balance(args.from_id)
    if from_bal < args.amount:
        Logger.error("Admin", f"送り元の残高不足です ({from_bal} pts)")
        return

    # 履歴とログを残すため手動で実施
    wallet.save_balance(args.from_id, from_bal - args.amount)
    wallet.add_history(args.from_id, f"{args.reason} (to {args.to_id})", -args.amount)

    to_bal = wallet.load_balance(args.to_id)
    wallet.save_balance(args.to_id, to_bal + args.amount)
    wallet.add_history(args.to_id, f"{args.reason} (from {args.from_id})", args.amount)

    Logger.info(
        "Admin", f"DONE: {args.from_id} -> {args.to_id} へ {args.amount} pts 移動しました。"
    )


def handle_compensate(args):
    # BetService.payout を使用して一貫性を保つ
    actual = BetService.payout(args.user_id, args.amount, reason=args.reason)
    current = wallet.load_balance(args.user_id)
    Logger.info(
        "Admin",
        f"DONE: {args.user_id} に {actual} pts 補填しました。(理由: {args.reason}, 新残高: {current} pts)",
    )


def handle_balance(args):
    bal = wallet.load_balance(args.user_id)
    Logger.info("Admin", f"User {args.user_id} Balance: {bal} pts")


def handle_check_status(args):
    from logic.economy.status import StatusService

    uid = args.user_id
    bal = wallet.load_balance(uid)
    status = StatusService.get_user_status(uid)
    benchmark = StatusService.get_benchmark()
    threshold = benchmark * StatusService.SN_THRESHOLD_RATE

    Logger.info("Admin", f"--- User Status: {uid} ---")
    Logger.info("Admin", f"Balance: {bal} pts")
    Logger.info("Admin", f"Status: {status}")
    Logger.info("Admin", f"Current Benchmark: {benchmark:.0f} pts")
    Logger.info("Admin", f"Standard Threshold (30%): {threshold:.0f} pts")


def handle_daily(args):
    success, message = BetService.claim_daily(args.user_id, force=args.force)
    if success:
        Logger.info("Admin", f"DONE: {args.user_id} のデイリーボーナスを実行しました。 {message}")
    else:
        Logger.info(
            "Admin",
            f"SKIP: {args.user_id} のデイリーボーナス実行をスキップしました。 {message}",
        )


def handle_hard_cancel(args):
    from core.handlers.storage import SQLiteSessionRepository

    session_repo = SQLiteSessionRepository()
    session_model = session_repo.get_session(args.channel_id)
    if not session_model:
        Logger.error(
            "Admin",
            f"Channel {args.channel_id} にアクティブなセッションは見つかりませんでした。",
        )
        return

    session_data = session_model.model_dump()

    if args.refund:
        bet_amount = session_data.get("bet_amount", 0)
        players = session_data.get("players", [])
        for p in players:
            uid = p.get("id")
            if uid:
                # BetService.payout を使って返金
                actual = BetService.payout(
                    uid, bet_amount, reason=f"ADMIN HARD_CANCEL REFUND (Ch:{args.channel_id})"
                )
                Logger.info("Admin", f"REFUND: User {uid} に {actual} pts 返金しました。")

    session_repo.delete_session(args.channel_id)
    Logger.info("Admin", f"DONE: Channel {args.channel_id} のセッションを強制削除しました。")


def handle_revive(args):
    from core.handlers.storage import SQLiteDobumonRepository
    from logic.dobumon.core.dob_manager import DobumonManager

    repo = SQLiteDobumonRepository()
    manager = DobumonManager(repo)
    success, message = manager.revive_dobumon_by_name(args.name)
    if success:
        Logger.info("Admin", message)
    else:
        Logger.error("Admin", message)


def handle_dobumon_rename(args):
    from core.handlers.storage import SQLiteDobumonRepository
    from logic.dobumon.core.dob_manager import DobumonManager

    repo = SQLiteDobumonRepository()
    manager = DobumonManager(repo)
    success, message = manager.rename_dobumon_by_name(args.old_name, args.new_name)
    if success:
        Logger.info("Admin", message)
    else:
        Logger.error("Admin", message)


def main():
    parser = argparse.ArgumentParser(description="Discord Economy System 管理ツール (CLI)")
    subparsers = parser.add_subparsers(dest="command", help="サブコマンド")

    # give
    parser_give = subparsers.add_parser("give", help="ユーザーにポイントを付与します")
    parser_give.add_argument("user_id", type=int, help="対象ユーザーID")
    parser_give.add_argument("amount", type=int, help="付与するポイント数")
    parser_give.add_argument("--reason", default="管理者による付与", help="理由")

    # remove
    parser_remove = subparsers.add_parser("remove", help="ユーザーからポイントを差し引きます")
    parser_remove.add_argument("user_id", type=int, help="対象ユーザーID")
    parser_remove.add_argument("amount", type=int, help="差し引くポイント数")
    parser_remove.add_argument("--reason", default="管理者による回収", help="理由")

    # transfer
    parser_transfer = subparsers.add_parser("transfer", help="ユーザー間でポイントを移動します")
    parser_transfer.add_argument("from_id", type=int, help="送り元ユーザーID")
    parser_transfer.add_argument("to_id", type=int, help="送り先ユーザーID")
    parser_transfer.add_argument("amount", type=int, help="移動するポイント数")
    parser_transfer.add_argument("--reason", default="管理者による移動", help="理由")

    # compensate
    parser_compensate = subparsers.add_parser("compensate", help="ユーザーに補填を行います")
    parser_compensate.add_argument("user_id", type=int, help="対象ユーザーID")
    parser_compensate.add_argument("amount", type=int, help="補填するポイント数")
    parser_compensate.add_argument("--reason", default="補填対応", help="理由")

    # balance
    parser_bal = subparsers.add_parser("balance", help="ユーザーの残高を表示します")
    parser_bal.add_argument("user_id", type=int, help="ユーザーID")

    # daily
    parser_daily = subparsers.add_parser("daily", help="ユーザーのデイリーボーナスを強制実行します")
    parser_daily.add_argument("user_id", type=int, help="対象ユーザーID")
    parser_daily.add_argument("--force", action="store_true", help="受け取り済みでも強制実行します")

    # check_status
    parser_status = subparsers.add_parser(
        "check_status", help="ユーザーのステータスと現在のベンチマークを表示します"
    )
    parser_status.add_argument("user_id", type=int, help="対象ユーザーID")

    # hard_cancel
    parser_cancel = subparsers.add_parser("hard_cancel", help="稼働中のセッションを強制削除します")
    parser_cancel.add_argument("channel_id", type=int, help="対象チャンネルID")
    parser_cancel.add_argument("--refund", action="store_true", help="参加者に参加費を返金します")

    # revive (dobumon)
    parser_revive = subparsers.add_parser("revive", help="死亡した怒武者を生き返らせます")
    parser_revive.add_argument("name", type=str, help="対象の怒武者名")

    # dobumon_rename (dobumon)
    parser_rename = subparsers.add_parser("dobumon_rename", help="怒武者の名前を変更します")
    parser_rename.add_argument("old_name", type=str, help="現在の名前")
    parser_rename.add_argument("new_name", type=str, help="新しい名前")

    args = parser.parse_args()

    handlers = {
        "give": handle_give,
        "remove": handle_remove,
        "transfer": handle_transfer,
        "compensate": handle_compensate,
        "balance": handle_balance,
        "check_status": handle_check_status,
        "daily": handle_daily,
        "hard_cancel": handle_hard_cancel,
        "revive": handle_revive,
        "dobumon_rename": handle_dobumon_rename,
    }

    if args.command in handlers:
        handlers[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
