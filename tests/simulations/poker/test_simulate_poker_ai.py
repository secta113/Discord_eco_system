import asyncio
import multiprocessing
import os
import random
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core.utils.logger import Logger
from logic.poker.ai import get_ai_instance
from logic.poker.pk_service import TexasPokerService


# モック用のグローバル関数（各プロセスで呼び出される）
def setup_mocks(human_is_prime, stats_ref=None):
    # モック：wallet関連（DBアクセス遮断）
    from core.economy import wallet

    # 全ユーザーの残高取得をモック
    wallet.get_all_balances = lambda: {999: 100000, 0: 500000}
    # 個別残高ロードをモック
    wallet.load_balance = lambda uid: 100000 if uid > 0 else 500000
    # 書き込み系を無効化
    wallet.update_stats = lambda *args, **kwargs: None
    wallet.save_balance = lambda *args, **kwargs: None
    wallet.add_history = lambda *args, **kwargs: None

    # モック：BetService.get_user_status を差し替え
    from logic.bet_service import BetService

    BetService.get_user_status = lambda uid: "Prime" if human_is_prime and uid > 0 else "Standard"

    # モック：JackpotService.add_to_jackpot を差し替え
    from logic.economy.jackpot import JackpotService

    def mock_add_to_jackpot(amount):
        if stats_ref is not None:
            stats_ref["total_payout_to_jackpot"] += amount

    JackpotService.add_to_jackpot = mock_add_to_jackpot

    # execute_jackpot (jackpot_logsへのDB書き込み) も完全に遮断したいが、
    # グローバルな書き換えは後続のテストに影響するため、各テストケースのパッチに任せる

    # ロガー設定
    import logging

    logging.getLogger("Poker").setLevel(logging.WARNING)
    logging.getLogger("PokerAI").setLevel(logging.WARNING)


def run_single_game(args):
    target_players, human_is_prime, seed = args
    # 各プロセスで個別のシードを設定
    random.seed(seed)
    setup_mocks(human_is_prime)

    game_stats = {
        "rank_counts": Counter(),
        "win_counts": Counter(),
        "profit_sum": Counter(),
        "total_payout_to_jackpot": 0,
        "human_wins": 0,
        "human_profit_sum": 0,
        "cheat_count": 0,
    }

    # 再度モック（Jackpot加算用）
    from logic.economy.jackpot import JackpotService

    def local_add_to_jackpot(amount):
        game_stats["total_payout_to_jackpot"] += amount

    JackpotService.add_to_jackpot = local_add_to_jackpot

    # セッション作成
    session = TexasPokerService(channel_id=123, bet_amount=100, target_player_count=target_players)

    # 人間プレイヤー追加
    human_id = 999
    session.add_player(
        type("User", (), {"id": human_id, "display_name": "Human", "mention": "@Human"})
    )

    # ゲーム開始（NPCの自動補充が行われる）
    session.start_game()

    # 参加したAIランクを記録
    for p in session.player_states.values():
        if p.is_npc:
            game_stats["rank_counts"][p.ai_rank] += 1

    # ゲーム進行（showdownまで）
    while session.phase != "showdown" and session.status == "playing":
        current_p = session.get_current_player()
        if not current_p:
            break

        p_state = session.player_states[current_p["id"]]

        if p_state.is_npc:
            ai = get_ai_instance(p_state)
            if p_state.ai_rank == "monster" and session.phase == "river":
                old_cards = list(p_state.hole_cards)
                ai.cheat_hand(session)
                if old_cards != p_state.hole_cards:
                    game_stats["cheat_count"] += 1
            action, amount = ai.decide_action(session)
            session.handle_action(p_state.user_id, action, amount)
        else:
            r = random.random()
            if r < 0.5:
                needed = session.current_max_bet - p_state.current_bet
                session.handle_action(human_id, "call" if needed > 0 else "check", 0)
            elif r < 0.8:
                # 0 を渡すと内部で自動的に「最小レイズ額」が計算される
                session.handle_action(human_id, "raise", 0)
            else:
                session.handle_action(human_id, "fold", 0)

    # 精算
    results, rake = session.settle_game()

    # 勝者の統計を取る
    winnings = {}
    for r in results:
        if r.get("profit", 0) > 0:
            p_id = r["id"]
            winnings[p_id] = r["profit"]
            p_state = session.player_states.get(p_id)
            if p_state and p_state.is_npc:
                game_stats["win_counts"][p_state.ai_rank] += 1
            else:
                game_stats["human_wins"] += 1

    # 各NPC・Humanのチップの増減(利益)を集計
    buyin = session.buyin_amount
    for p_state in session.player_states.values():
        final_chips = p_state.stack + winnings.get(p_state.user_id, 0)
        net_profit = final_chips - buyin

        if p_state.is_npc:
            game_stats["profit_sum"][p_state.ai_rank] += net_profit
        else:
            game_stats["human_profit_sum"] += net_profit

    return game_stats


def run_simulation_parallel(num_games=1000, target_players=4, human_is_prime=False):
    print(f"--- Parallel Poker AI Simulation Start ({num_games} games, CPUS: {os.cpu_count()}) ---")
    start_time = time.time()

    combined_stats = {
        "rank_counts": Counter(),
        "win_counts": Counter(),
        "profit_sum": Counter(),
        "total_payout_to_jackpot": 0,
        "human_wins": 0,
        "human_profit_sum": 0,
        "cheat_count": 0,
    }

    # タスクの準備
    seeds = [random.randint(0, 1000000) for _ in range(num_games)]
    tasks = [(target_players, human_is_prime, s) for s in seeds]

    # プロセスプールで実行
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        futures = [executor.submit(run_single_game, t) for t in tasks]

        count = 0
        for future in as_completed(futures):
            res = future.result()
            # 結果の集計
            combined_stats["rank_counts"].update(res["rank_counts"])
            combined_stats["win_counts"].update(res["win_counts"])
            combined_stats["profit_sum"].update(res["profit_sum"])
            combined_stats["total_payout_to_jackpot"] += res["total_payout_to_jackpot"]
            combined_stats["human_wins"] += res["human_wins"]
            combined_stats["human_profit_sum"] += res["human_profit_sum"]
            combined_stats["cheat_count"] += res.get("cheat_count", 0)

            count += 1
            if count % 100 == 0:
                print(f"Progress: {count}/{num_games}...")

    end_time = time.time()
    print(f"\n--- Simulation Results ({end_time - start_time:.2f}s) ---")
    print(f"Total Games: {num_games}")
    print(f"Total NPCs Spawned: {sum(combined_stats['rank_counts'].values())}")
    for rank in ["monster", "legendary", "rare", "common", "trash"]:
        count = combined_stats["rank_counts"][rank]
        wins = combined_stats["win_counts"][rank]
        profit = combined_stats["profit_sum"][rank]
        win_rate = (wins / count * 100) if count > 0 else 0
        avg_profit = (profit / count) if count > 0 else 0
        appearance_rate = count / (num_games * (target_players - 1)) * 100

        if rank == "monster":
            cheat_rate = (combined_stats["cheat_count"] / count * 100) if count > 0 else 0
            print(
                f"[{rank.upper()}] Count: {count} ({appearance_rate:.1f}%), Wins: {wins}, Win Rate: {win_rate:.1f}%, Avg Profit: {avg_profit:+.1f} pts, Cheat Rate: {cheat_rate:.1f}%"
            )
        else:
            print(
                f"[{rank.upper()}] Count: {count} ({appearance_rate:.1f}%), Wins: {wins}, Win Rate: {win_rate:.1f}%, Avg Profit: {avg_profit:+.1f} pts"
            )

    avg_human_profit = combined_stats["human_profit_sum"] / num_games
    print(
        f"[HUMAN] Wins: {combined_stats['human_wins']} (Rate: {combined_stats['human_wins'] / num_games * 100:.1f}%), Avg Profit: {avg_human_profit:+.1f} pts"
    )
    print(f"Total Points pooled to Jackpot: {combined_stats['total_payout_to_jackpot']} pts")


def test_poker_ai_simulation_runs():
    """
    自動テスト（pytest / CI）用のエントリーポイント。
    """
    from unittest.mock import patch

    from core.economy import wallet
    from logic.bet_service import BetService

    # グローバル汚染を防ぐため、このテスト内では patch コンテキストマネージャを使用する
    # run_single_game 内部で呼び出される setup_mocks が副作用を残さないよう、モック化する
    with (
        patch("tests.simulations.poker.test_simulate_poker_ai.setup_mocks"),
        patch.object(wallet, "get_all_balances", return_value={999: 100000, 0: 500000}),
        patch.object(wallet, "load_balance", side_effect=lambda uid: 100000 if uid > 0 else 500000),
        patch.object(wallet, "update_stats", return_value=None),
        patch.object(wallet, "save_balance", return_value=None),
        patch.object(wallet, "add_history", return_value=None),
        patch.object(BetService, "get_user_status", return_value="Prime"),
    ):
        for i in range(5):
            result = run_single_game((3, True, i))
            assert isinstance(result, dict)
            assert "human_wins" in result


if __name__ == "__main__":
    # 多重実行時のガード
    multiprocessing.freeze_support()

    # 直接実行された場合は、本格的なシミュレーション（15000回）を回す
    run_simulation_parallel(num_games=15000, target_players=4, human_is_prime=True)
