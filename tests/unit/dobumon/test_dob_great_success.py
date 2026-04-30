import random
from unittest.mock import MagicMock

import pytest

from core.handlers.storage import IDobumonRepository
from logic.dobumon.core.dob_manager import DobumonManager
from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.training import TrainingEngine


@pytest.fixture
def mock_repo():
    return MagicMock(spec=IDobumonRepository)


@pytest.fixture
def manager(mock_repo):
    return DobumonManager(mock_repo)


def test_great_success_probability_base():
    """絆0の時の基本大成功率（10%）を検証"""
    dobu = Dobumon(
        dobumon_id="test",
        owner_id=1,
        name="Test",
        gender="M",
        hp=100.0,
        atk=50.0,
        defense=50.0,
        eva=10.0,
        spd=20.0,
        affection=0,
    )

    trials = 1000
    great_count = 0
    # 決定論的なテストのためにシードを固定するか、回数を増やす
    random.seed(42)
    for _ in range(trials):
        result = TrainingEngine.calculate_menu_gains(dobu, "strength")
        if result.get("is_great"):
            great_count += 1

    # 10% 前後であることを確認 (90-110回程度)
    assert 80 <= great_count <= 120


def test_great_success_probability_with_affection():
    """絆100の時の大成功率（20%）を検証"""
    dobu = Dobumon(
        dobumon_id="test",
        owner_id=1,
        name="Test",
        gender="M",
        hp=100.0,
        atk=50.0,
        defense=50.0,
        eva=10.0,
        spd=20.0,
        affection=100,
    )

    trials = 1000
    great_count = 0
    random.seed(42)
    for _ in range(trials):
        result = TrainingEngine.calculate_menu_gains(dobu, "strength")
        if result.get("is_great"):
            great_count += 1

    # 20% 前後であることを確認
    assert 180 <= great_count <= 220


def test_burst_trait_bonus():
    """「爆発」特性による大成功率の2倍ボーナスと上限（70%）を検証"""
    # 絆0 + 爆発 = 10% * 2 = 20%
    dobu_burst = Dobumon(
        dobumon_id="burst",
        owner_id=1,
        name="Burst",
        gender="M",
        hp=100.0,
        atk=50.0,
        defense=50.0,
        eva=10.0,
        spd=20.0,
        affection=0,
        traits=["burst"],
    )

    random.seed(42)
    trials = 1000
    great_count = 0
    for _ in range(trials):
        result = TrainingEngine.calculate_menu_gains(dobu_burst, "strength")
        if result.get("is_great"):
            great_count += 1

    assert 180 <= great_count <= 220

    # 絆400 + 爆発 = (10%+40%) * 2 = 100% -> Cap 70%
    dobu_burst_max = Dobumon(
        dobumon_id="burst_max",
        owner_id=1,
        name="BurstMax",
        gender="M",
        hp=100.0,
        atk=50.0,
        defense=50.0,
        eva=10.0,
        spd=20.0,
        affection=400,
        traits=["burst"],
    )

    great_count = 0
    for _ in range(trials):
        result = TrainingEngine.calculate_menu_gains(dobu_burst_max, "strength")
        if result.get("is_great"):
            great_count += 1

    # 70% 前後であることを確認
    assert 650 <= great_count <= 750


def test_great_success_stat_multiplier():
    """大成功時にステータス上昇量が1.5倍になることを検証"""
    dobu = Dobumon(
        dobumon_id="test",
        owner_id=1,
        name="Test",
        gender="M",
        hp=100.0,
        atk=50.0,
        defense=50.0,
        eva=10.0,
        spd=20.0,
        affection=0,
    )

    # random.random を 0 に固定して大成功を確実にする
    with MagicMock() as mock_random:
        import random as real_random

        # TrainingEngine 内部で使われている random.random をパッチ
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr("logic.dobumon.training.dob_train.random.random", lambda: 0.0)
            mp.setattr(
                "logic.dobumon.training.dob_train.random.uniform", lambda a, b: 1.0
            )  # 分散なし

            result = TrainingEngine.calculate_menu_gains(dobu, "strength")
            assert result["is_great"] is True

            # 通常時の計算 (great_multiplierなし) を手動で行う
            # ATK weight=4, Total=7, Scale=5.0, IV=1.0, Stage=1.0 (prime assumed)
            # unit = 4/7 * 5.0 = 2.857
            # gain = 2.86 * 1.5 = 4.29...?
            # 実際の実装では round(gain, 2)

            # 大成功なしの期待値と比較
            mp.setattr("logic.dobumon.training.dob_train.random.random", lambda: 0.99)  # 大成功なし
            result_normal = TrainingEngine.calculate_menu_gains(dobu, "strength")

            for stat in result["gains"]:
                if result_normal["gains"][stat] != 0:
                    assert result["gains"][stat] == pytest.approx(
                        result_normal["gains"][stat] * 1.5, abs=0.1
                    )


def test_great_success_affection_bonus(manager, mock_repo):
    """大成功時に絆が+2されることを検証"""
    dobu = Dobumon(
        dobumon_id="test_aff",
        owner_id=str(1),
        name="AffTester",
        gender="M",
        hp=100.0,
        atk=50.0,
        defense=50.0,
        eva=10.0,
        spd=20.0,
        affection=10,
        today_affection_gain=0,
    )

    # セーブされた内容を dobu に反映する
    def save_effect(model):
        data = model.model_dump()
        for k, v in data.items():
            setattr(dobu, k, v)

    mock_repo.save_dobumon.side_effect = save_effect

    # 常に最新の dobu をラップした mock_model を返す
    def get_effect(id):
        m = MagicMock()
        m.model_dump.return_value = dobu.to_dict()
        return m

    mock_repo.get_dobumon.side_effect = get_effect

    # 大成功を確定させる
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("logic.dobumon.training.dob_train.random.random", lambda: 0.0)
        mp.setattr("logic.dobumon.training.dob_train.random.uniform", lambda a, b: 1.0)

        manager.train_menu("test_aff", "strength")

        # セーブされた内容を確認
        updated_dobu = manager.get_dobumon("test_aff")
        assert updated_dobu.affection == 12  # 10 + 2
        assert updated_dobu.today_affection_gain == 2
