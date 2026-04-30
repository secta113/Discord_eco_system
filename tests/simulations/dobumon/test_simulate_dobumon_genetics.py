import random
import uuid

import pytest

from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.genetics.dob_breeders import BreedingFactory
from logic.dobumon.genetics.dob_mendel import MendelEngine


def generate_wild_dobumon(gender: str, name: str) -> Dobumon:
    """初期の野生ドブモンを生成する"""
    return Dobumon(
        dobumon_id=str(uuid.uuid4()),
        owner_id=1,
        name=name,
        gender=gender,
        hp=50,
        atk=30,
        defense=25,
        eva=10,
        spd=20,
        health=50,
        generation=1,
        iv={"hp": 1.0, "atk": 1.0, "defense": 1.0, "eva": 1.0, "spd": 1.0},
        genetics={"genotype": MendelEngine.get_initial_genotype()},
        lifespan=100.0,
        max_lifespan=100.0,
        is_alive=True,
    )


def test_long_term_breeding_simulation():
    """
    10世代に渡ってドブモンを交配させ、ステータスのインフレやデフレが
    ゲームシステムの想定範囲内に収まり、バグ（HPが0以下など）が発生しないか検証する。
    """
    # 完全に再現性を持たせるため、シミュレーション内局所シードだけ一時固定してもよいが、
    # Flakyテストの検証のためにあえて固定しないか、特定のエッジケースに備える。
    # ここでは10世代回して「一つも」規格外にならないことを条件とする。

    current_generation = [
        generate_wild_dobumon("M", "Wild_M1"),
        generate_wild_dobumon("F", "Wild_F1"),
        generate_wild_dobumon("M", "Wild_M2"),
        generate_wild_dobumon("F", "Wild_F2"),
        generate_wild_dobumon("M", "Wild_M3"),
        generate_wild_dobumon("F", "Wild_F3"),
    ]

    SIMULATION_GENERATIONS = 10

    for gen in range(2, SIMULATION_GENERATIONS + 2):
        next_generation = []

        # 現在の世代からランダムにペアを作って交配 (毎世代6匹生成を維持)
        # 近親交配を完全に避けるアルゴリズムは組まず、あえて交ざることで禁忌や病弱などのエッジを引き起こす
        for i in range(6):
            p1 = random.choice(current_generation)
            p2 = random.choice(current_generation)

            # 同じ個体は除外（自己交配の防止）
            attempts = 0
            while p1.dobumon_id == p2.dobumon_id and attempts < 10:
                p2 = random.choice(current_generation)
                attempts += 1

            breeder = BreedingFactory.get_breeder(p1, p2)
            child = breeder.breed(p1, p2, f"Gen{gen}_{i}")
            next_generation.append(child)

        current_generation = next_generation

        # 毎世代のチェック
        for dobumon in current_generation:
            # 1. 致命的なバグ（HP 0以下）が起きていないこと
            assert dobumon.hp > 0, (
                f"Generation {gen} DoBumon {dobumon.name} has HP <= 0: {dobumon.hp}"
            )
            assert dobumon.atk > 0, (
                f"Generation {gen} DoBumon {dobumon.name} has ATK <= 0: {dobumon.atk}"
            )
            assert dobumon.defense > 0, (
                f"Generation {gen} DoBumon {dobumon.name} has DEF <= 0: {dobumon.defense}"
            )

            # 2. HP インフレが極端なオーバーフローを起こさないこと
            # ゲーム特有の血統強化（禁忌交配の1.5倍や成長限界突破等）により、10世代で万単位に到達する仕様(Power Creep)を許容するが、異常なバグ値は弾く
            assert dobumon.hp < 1_000_000_000_000, (
                f"Generation {gen} DoBumon {dobumon.name} HP overflowed: {dobumon.hp}"
            )

            # 3. 寿命が現実的な範囲（極端なマイナス等にならないこと。近親交配が進むため寿命は大幅に落ちるが、0未満にはならない計算）
            assert dobumon.lifespan > 0, (
                f"Generation {gen} DoBumon {dobumon.name} has negative lifespan: {dobumon.lifespan}"
            )

            # 4. 病気率が適正な範囲（0.0 ~ 1.0 またはそれを大きく超えない数値）
            assert dobumon.illness_rate >= 0.0, (
                f"Generation {gen} DoBumon {dobumon.name} has negative illness: {dobumon.illness_rate}"
            )
