import pytest

from core.economy import wallet
from logic.constants import GameType, JPRarity
from logic.economy.jackpot import JackpotService


def setup_economy(total_circulation):
    """
    テスト用の経済規模をセットアップする。
    """
    dummy_user_id = 9999
    wallet.save_balance(dummy_user_id, total_circulation)
    JackpotService._save_pool(0)


def test_jackpot_calculation_v22(init_test_env):
    """v2.2 動的計算の基本テスト"""
    tc = 10000000  # 10,000,000 (10M)
    setup_economy(tc)

    # 1. 普通のケース: プール十分
    JackpotService._save_pool(1000000)  # 1M

    # RARE (10% of Pool = 100k)
    # TC-based Hard Cap (5% of 10M = 500k)
    # Chinchiro Game Cap (20% of 1M = 200k)
    # 期待値: 100,000
    payout = JackpotService.calculate_payout(GameType.CHINCHIRO, JPRarity.RARE)
    assert payout == 100000

    # 2. 上限ケース: プール巨大
    JackpotService._save_pool(5000000)  # 5M
    # RARE (10% of Pool = 500k)
    # TC-based Hard Cap (5% of 10M = 500k)
    # Chinchiro Game Cap (20% of 5M = 1M)
    # 期待値: 500,000 (Hard Cap ちょうど)
    payout = JackpotService.calculate_payout(GameType.CHINCHIRO, JPRarity.RARE)
    assert payout == 500000

    # RARE でプールがさらに巨大 (1,000万) な場合
    JackpotService._save_pool(10000000)  # 10M
    # RARE (10% of Pool = 1M)
    # TC-based Hard Cap (5% of 10M = 500k)
    # 期待値: 500,000 (Hard Cap で制限)
    payout = JackpotService.calculate_payout(GameType.CHINCHIRO, JPRarity.RARE)
    assert payout == 500000


def test_min_payout_guarantee(init_test_env):
    """最低保証額とシステム補填のテスト"""
    tc = 10000000  # 10M
    setup_economy(tc)

    # プールを極小 (1,000) にセット
    JackpotService._save_pool(1000)

    # LEGENDARY (100% of Pool = 1,000)
    # TC-based Min Payout (2% of 10M = 200k)
    # 期待値: 200,000
    payout = JackpotService.calculate_payout(GameType.POKER, JPRarity.LEGENDARY)
    assert payout == 200000

    # 実際に放出を実行し、システム補填が行われることを確認
    # execute_jackpot は BetService.execute_jackpot 経由、または直接
    user_id = 123
    wallet.save_balance(user_id, 0)

    # モックではない実際の execute_jackpot
    def payout_func(uid, amt, reason):
        wallet.save_balance(uid, wallet.load_balance(uid) + amt)

    final_payout = JackpotService.execute_jackpot(
        user_id, GameType.POKER, JPRarity.LEGENDARY, "Royal Flush", payout_func
    )

    assert final_payout == 200000
    assert wallet.load_balance(user_id) == 200000
    assert JackpotService._load_pool() == 0  # プールは全額放出されて 0


def test_game_ratio_caps(init_test_env):
    """ゲームごとの比率制限テスト"""
    tc = 10000000  # 10M (経済規模を小さくしてMin Payout越えを防ぐ)
    setup_economy(tc)

    # プール 5,000,000 (5M)
    JackpotService._save_pool(5000000)

    # チンチロ (LEGENDARY 100% -> Game Cap 20% of 5M = 1M)
    payout = JackpotService.calculate_payout(GameType.CHINCHIRO, JPRarity.LEGENDARY)
    assert payout == 1000000

    # ブラックジャック (LEGENDARY 100% -> Game Cap 50% of 5M = 2.5M)
    payout = JackpotService.calculate_payout(GameType.BLACKJACK, JPRarity.LEGENDARY)
    assert payout == 2500000

    # ポーカー (LEGENDARY 100% -> Game Cap 100% of 5M = 5M)
    payout = JackpotService.calculate_payout(GameType.POKER, JPRarity.LEGENDARY)
    assert payout == 5000000


def test_rarity_hierarchy(init_test_env):
    """経済規模に関わらずレアリティの階層が維持されているか"""
    tc = 1000000  # 1M
    setup_economy(tc)

    JackpotService._save_pool(1000000)

    l_pay = JackpotService.calculate_payout(GameType.POKER, JPRarity.LEGENDARY)
    e_pay = JackpotService.calculate_payout(GameType.POKER, JPRarity.EPIC)
    r_pay = JackpotService.calculate_payout(GameType.POKER, JPRarity.RARE)
    c_pay = JackpotService.calculate_payout(GameType.POKER, JPRarity.COMMON)

    assert l_pay > e_pay > r_pay > c_pay


def test_rarity_none_v22(init_test_env):
    """NONE の場合は放出されないこと"""
    setup_economy(1000000)
    JackpotService._save_pool(1000000)
    payout = JackpotService.calculate_payout(GameType.POKER, JPRarity.NONE)
    assert payout == 0
