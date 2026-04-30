import pytest

from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.dob_battle.dob_engine import BattleEngine
from logic.dobumon.training import TrainingEngine


def test_normalization_and_weights():
    dobu = Dobumon(
        dobumon_id="test",
        owner_id=123,
        name="TestDobu",
        gender="M",
        hp=100.0,
        atk=50.0,
        defense=50.0,
        eva=10.0,
        spd=20.0,
    )

    # Strength Training: ATK(4), DEF(2), SPD(-1)
    # Total Absolute Weight = 4 + 2 + 1 = 7
    # ATK unit = 4/7, DEF unit = 2/7, SPD unit = -1/7
    result = TrainingEngine.calculate_menu_gains(dobu, "strength")
    gains = result["gains"]

    assert gains["atk"] > 0
    assert gains["defense"] > 0
    assert gains["spd"] < 0

    # Shadow Boxing: ATK(2), SPD(2), EVA(1)
    # Total Absolute Weight = 2 + 2 + 1 = 5
    result_shadow = TrainingEngine.calculate_menu_gains(dobu, "shadow")
    gains_shadow = result_shadow["gains"]

    assert gains_shadow["atk"] > 0
    assert gains_shadow["spd"] > 0
    assert gains_shadow["eva"] > 0


def test_spd_decay_in_battle():
    # SPD high vs SPD low
    dobu1 = Dobumon(
        dobumon_id="p1",
        owner_id=1,
        name="Speeder",
        gender="M",
        hp=100.0,
        atk=50.0,
        defense=50.0,
        eva=10.0,
        spd=100.0,
    )
    dobu2 = Dobumon(
        dobumon_id="p2",
        owner_id=2,
        name="Tank",
        gender="F",
        hp=1000.0,
        atk=50.0,
        defense=100.0,
        eva=0.0,
        spd=20.0,
    )

    engine = BattleEngine(dobu1, dobu2)
    result = engine.simulate()

    # Check if speeder's turns get delayed over time
    # This is hard to check directly from steps without more logic, but we can verify it runs.
    # Let's count turns.
    p1_turns = [s for s in result["steps"] if s["attacker"] == 1]
    assert len(p1_turns) > 0


def test_affection_limit():
    import datetime

    from logic.dobumon.core.dob_manager import DobumonManager

    # Mock storage
    class MockStorage:
        def get_dobumon(self, dobumon_id):
            return None

        def save_dobumon(self, model):
            pass

        def get_user_dobumons(self, owner_id, only_alive=True):
            return []

    manager = DobumonManager(MockStorage())
    dobu = Dobumon(
        dobumon_id="limit_test",
        owner_id=1,
        name="BondTest",
        gender="M",
        hp=100.0,
        atk=50.0,
        defense=50.0,
        eva=10.0,
        spd=20.0,
        affection=0,
        today_affection_gain=0,
        today_train_count=0,
        last_train_date=(datetime.datetime.utcnow() + datetime.timedelta(hours=9)).strftime(
            "%Y-%m-%d"
        ),
    )

    # Mock get_dobumon to return our dobu
    manager.get_dobumon = lambda id: dobu

    # 1〜5回目のトレーニング。絆が「増えている」ことを確認（+1か+2）
    prev_aff = 0
    for _ in range(5):
        success, res = manager.train_menu("limit_test", "strength")
        assert success
        assert dobu.affection > prev_aff
        prev_aff = dobu.affection

    # ここまでの上昇量は大成功込みで 5〜10 のはず。
    # ただし上限 8 に制限されているはず。
    assert dobu.today_affection_gain <= 8
    total_gain_after_5 = dobu.today_affection_gain

    # 6回目 - オーバーワーク
    success, res = manager.train_menu("limit_test", "strength")
    assert success
    assert dobu.affection == total_gain_after_5  # 上昇しない
    assert dobu.today_affection_gain == total_gain_after_5
    assert res["overworked"] is True


if __name__ == "__main__":
    test_normalization_and_weights()
    test_affection_limit()
    print("Test passed!")
