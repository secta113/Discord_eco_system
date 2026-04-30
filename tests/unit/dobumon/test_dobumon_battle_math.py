import random
from unittest.mock import patch

import pytest

from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.dob_battle.dob_calculator import BattleCalculator
from logic.dobumon.dob_battle.dob_engine import BattleEngine


def create_dobu(id, atk, df, spd, attr="fire"):
    return Dobumon(
        dobumon_id=str(id),
        owner_id=1,
        name=f"Dobu-{id}",
        gender="M",
        hp=1000,
        atk=atk,
        defense=df,
        eva=10,
        spd=spd,
        attribute=attr,
    )


def test_damage_ratios():
    """ダメージ比率式が期待通りの範囲に収まるか検証"""
    calc = BattleCalculator()
    random.seed(
        42
    )  # 決定論的なテストのためにシード固定 (ただし calculator 内で random 呼ぶので注意)

    # 乱数分散を無視するために極端な回数試行して平均を見るか、
    # 1.0 (等倍) のケースを想定してロジックレベルで検証するか

    # シナリオ1: 低ステータス同士 (Atk:50 vs Def:40)
    # Base = (50*50)/(50+40) = 2500 / 90 = 27.77
    d1 = create_dobu(1, 50, 40, 10)
    d2 = create_dobu(2, 50, 40, 10)

    dmg_results = [calc.calculate_damage(d1, d2, 50)["damage"] for _ in range(100)]
    avg_dmg = sum(dmg_results) / 100
    assert 24 <= avg_dmg <= 31  # 27.77 +- 10% 程度

    # シナリオ2: ステータスギャップ (Atk:200 vs Def:100)
    # Base = (200*200)/(200+100) = 40000 / 300 = 133.33
    d3 = create_dobu(3, 200, 100, 10)
    d4 = create_dobu(4, 200, 100, 10)
    dmg_results = [calc.calculate_damage(d3, d4, 50)["damage"] for _ in range(100)]
    avg_dmg = sum(dmg_results) / 100
    assert 120 <= avg_dmg <= 150

    # シナリオ3: 極めて高いステータス (Atk:2000 vs Def:1500)
    # Base = (2000*2000)/(2000+1500) = 4,000,000 / 3500 = 1142.8
    d5 = create_dobu(5, 2000, 1500, 10)
    d6 = create_dobu(6, 2000, 1500, 10)
    dmg_results = [calc.calculate_damage(d5, d6, 50)["damage"] for _ in range(100)]
    avg_dmg = sum(dmg_results) / 100
    assert 1000 <= avg_dmg <= 1300


def test_atb_frequency():
    """SPD差による行動回数の比率を検証"""
    # SPD 100 vs SPD 50 (2:1の比率)
    d_fast = create_dobu("fast", 10, 10, 100)
    d_slow = create_dobu("slow", 10, 10, 50)

    # HPを高くして長期戦にする
    d_fast.hp = 10000
    d_slow.hp = 10000

    engine = BattleEngine(d_fast, d_slow)
    result = engine.simulate()
    steps = result["steps"]

    # 攻撃回数をカウント
    acts_fast = len([s for s in steps if s["attacker"] == 1])
    acts_slow = len([s for s in steps if s["attacker"] == 2])

    # 比率が約 2:1 であること (許容誤差を含める)
    # ※スタミナ減衰（疲労）が導入されたため、手数の多い個体ほど速度が落ち、比率は 2.0 より低めに出る傾向があります。
    ratio = acts_fast / acts_slow if acts_slow > 0 else acts_fast
    assert 1.4 <= ratio <= 2.2


def test_hit_and_miss():
    """回避が発生することを検証"""
    calc = BattleCalculator()
    # Atk.SPD=10, Def.EVA=100 (避けられやすい)
    # Hit = 1 - (100 / (10+100) * 0.5) = 1 - (0.909 * 0.5) = 1 - 0.454 = 0.545
    attacker = create_dobu("a", 10, 10, 10)
    defender = create_dobu("d", 10, 10, 10)
    defender.eva = 100

    hits = [calc.check_hit(attacker, defender, 100) for _ in range(1000)]
    hit_rate = sum(hits) / 1000
    assert 0.45 <= hit_rate <= 0.65


def test_critical_hit_math():
    """クリティカルヒットの倍率（1.3倍）が正確に適用されるか検証"""
    calc = BattleCalculator()

    # シナリオ: ATK 1000 vs DEF 40
    # Base = (1000*1000) / (1000 + 40) = 1,000,000 / 1040 = 961.538...
    attacker = create_dobu("a", 1000, 40, 100)
    defender = create_dobu("d", 1000, 40, 100)

    # random.random() < 0.05 でクリティカル発生 -> 0.0 を返せば確実
    # random.uniform(0.9, 1.1) で分散値を 1.0 (等倍) に固定
    with patch("random.random", return_value=0.0), patch("random.uniform", return_value=1.0):
        result = calc.calculate_damage(attacker, defender, 50)
        damage = result["damage"]
        is_crit = result["is_critical"]

        # 期待値: (1,000,000 / 1040) * 1.3 = 1,000,000 / 800 = 1250.0
        assert is_crit is True
        assert damage == 1250


def test_normal_hit_precision():
    """通常のヒットで float ステータスが正確に計算されるか検証"""
    calc = BattleCalculator()

    # float ステータス（微細な差）を設定
    # Atk: 50.5 vs Def: 40.0 -> (50.5^2)/90.5 = 2550.25 / 90.5 = 28.179...
    attacker = create_dobu("a", 50.5, 40.0, 10)
    defender = create_dobu("d", 50.5, 40.0, 10)

    with patch("random.random", return_value=0.5), patch("random.uniform", return_value=1.0):
        result = calc.calculate_damage(attacker, defender, 50)
        damage = result["damage"]

        # int(28.179...) = 28
        assert damage == 28

        # もし int 切り捨て済みの 50 vs 40 だったら -> (50^2)/90 = 27.77... -> 27
        # この 1 の差が float 化の価値


def test_hp_ceil_display():
    """HPが0.1でも残っている場合に、表示が1（切り上げ）になることを検証"""
    d1 = create_dobu(1, 10, 10, 100)
    d2 = create_dobu(2, 10, 10, 10)

    # D1のHPを0.1にする
    d1.health = 0.1
    d2.health = 100

    # D1 (HP:0.1) vs D2 (HP:100) でシミュレーション
    # D1が先手で動き、表示が 1 になっているか確認
    engine = BattleEngine(d1, d2)

    # 1ターン目でD1が動くように調整
    with patch("random.uniform", return_value=0.0):
        result = engine.simulate()
        steps = result["steps"]

        # ステップ1は戦闘開始。ステップ2が最初の行動
        # (timerが0になり actor1 が動く)
        first_action = steps[1]
        assert first_action["p1_hp"] == 1  # 0.1 -> ceil(0.1) = 1
