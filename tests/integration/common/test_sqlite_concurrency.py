import random
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from core.economy import wallet
from core.handlers.storage import SQLiteSystemRepository, SQLiteUserRepository


@pytest.fixture
def repo_setup(test_db_path, worker_id_cached):
    user_repo = SQLiteUserRepository(test_db_path)
    sys_repo = SQLiteSystemRepository(test_db_path)

    # Pre-populate some wallets to avoid "User not found" edge case if any code checks existence
    for i in range(10):
        # By default get_balance handles new users elegantly, but let's be sure.
        wallet.save_balance(i, 1000)

    yield user_repo, sys_repo


def worker_task(worker_id, user_id, sys_repo):
    """
    シミュレートされる個別のワーカータスク。
    DBに対して読み書き（トランザクション）を発生させる。
    """
    try:
        sys_repo.log_jackpot(user_id, "poker", "Royal Flush", "UR", 1000, 5000)
        return True, None
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            return False, e
        return False, e
    except Exception as e:
        return False, e


def test_sqlite_concurrency_no_locks(repo_setup):
    """
    高負荷時（多重スレッドアクセス時）に database is locked が発生せず、
    SQLite WAL と Timeout 設定によってクエリが正常に直列化されることを検証する。
    """
    user_repo, sys_repo = repo_setup

    THREAD_COUNT = 50
    # スレッドごとに 10 回登録
    ACTIONS_PER_THREAD = 10

    target_user_id = 999

    futures = []

    # 50 Threads concurrently hammering Jackpot Logs
    with ThreadPoolExecutor(max_workers=THREAD_COUNT) as executor:
        for t_idx in range(THREAD_COUNT):
            for a_idx in range(ACTIONS_PER_THREAD):
                futures.append(
                    executor.submit(worker_task, f"{t_idx}_{a_idx}", target_user_id, sys_repo)
                )

    errors = []
    locked_count = 0
    for f in as_completed(futures):
        success, err = f.result()
        if not success:
            if isinstance(err, sqlite3.OperationalError) and "database is locked" in str(err):
                locked_count += 1
            else:
                errors.append(err)

    # 検証1: エラーがないこと
    assert len(errors) == 0, f"Unexpected errors occurred: {errors}"
    assert locked_count == 0, (
        f"Database was locked {locked_count} times! Concurrency handling failed."
    )

    # 検証2: すべてのINSERTが正しくコミットされていること (Atomic updates)
    with sqlite3.connect(sys_repo.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM jackpot_logs")
        count = cursor.fetchone()[0]

    expected_count = THREAD_COUNT * ACTIONS_PER_THREAD

    assert count == expected_count, (
        f"Row count mismatch due to race condition. Expected {expected_count}, Got {count}."
    )
