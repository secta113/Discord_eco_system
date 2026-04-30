import threading
import time

import pytest

from core.economy import wallet
from core.utils.constants import GameType, JPRarity
from logic.economy.jackpot import JackpotService


def test_tc_cache_thread_safety(init_test_env):
    """TCキャッシュの並行アクセスにおけるスレッドセーフティを確認する"""
    # 初期セットアップ
    dummy_user_id = 8888
    # 既存ユーザーをクリア
    for uid in list(wallet.get_all_balances().keys()):
        wallet.save_balance(int(uid), 0)

    wallet.save_balance(dummy_user_id, 1000000)

    # キャッシュを強制クリア
    with JackpotService._tc_lock:
        JackpotService._tc_cache = None
        JackpotService._tc_cache_time = 0

    results = []

    def worker():
        try:
            tc = JackpotService.get_total_circulation()
            results.append(tc)
        except Exception as e:
            results.append(e)

    threads = []
    # 100スレッドで同時アクセス
    for _ in range(100):
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert len(results) == 100
    for r in results:
        if isinstance(r, Exception):
            raise r
        assert r >= 1000000


def test_concurrent_updates_and_reads(init_test_env):
    """更新と読み取りが同時に発生した場合の安全性を確認する"""
    dummy_user_id = 7777
    wallet.save_balance(dummy_user_id, 500000)

    # 短いTTLに設定して強制的に高頻度再計算を誘発
    original_ttl = JackpotService.TC_CACHE_TTL
    JackpotService.TC_CACHE_TTL = 0.001

    stop_event = threading.Event()
    errors = []

    def updater():
        try:
            for _ in range(100):
                if stop_event.is_set():
                    break
                bal = wallet.load_balance(dummy_user_id)
                wallet.save_balance(dummy_user_id, bal + 10)
                time.sleep(0.001)
        except Exception as e:
            errors.append(e)

    def reader():
        try:
            while not stop_event.is_set():
                tc = JackpotService.get_total_circulation()
                # 少なくとも初期値以上であるべき
                if tc < 500000:
                    errors.append(ValueError(f"Invalid TC detected: {tc}"))
                time.sleep(0.001)
        except Exception as e:
            errors.append(e)

    threads = []
    # 1つの更新スレッドと、10の読み取りスレッド
    threads.append(threading.Thread(target=updater))
    for _ in range(10):
        threads.append(threading.Thread(target=reader))

    for t in threads:
        t.start()

    time.sleep(0.5)
    stop_event.set()

    for t in threads:
        t.join()

    # TTLを戻す
    JackpotService.TC_CACHE_TTL = original_ttl

    if errors:
        raise errors[0]
