from unittest.mock import MagicMock

import pytest

from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.genetics.traits.registry import TraitRegistry


@pytest.fixture
def sample_dobu():
    return Dobumon(
        dobumon_id="test-id",
        owner_id=1,
        name="TestDobu",
        gender="M",
        hp=100.0,
        atk=50.0,
        defense=40.0,
        eva=10.0,
        spd=15.0,
        health=100.0,
        traits=[],
    )


def test_all_traits_evaluation(sample_dobu):
    all_keys = TraitRegistry.get_all_keys()
    failed_traits = []

    for key in all_keys:
        try:
            trait = TraitRegistry.get(key)
            # test basic methods
            trait.get_stat_multiplier("hp")
            trait.is_sterile()
            trait.can_extend_lifespan()

            # test apply_initial_status
            dobu_copy = Dobumon(
                dobumon_id="test-id",
                owner_id=1,
                name="TestDobu",
                gender="M",
                hp=100.0,
                atk=50.0,
                defense=40.0,
                eva=10.0,
                spd=15.0,
                health=100.0,
                traits=[key],
                genetics={"forbidden_depth": 1},
            )
            trait.apply_initial_status(dobu_copy)

            # test combat start
            opponent = Dobumon(
                dobumon_id="opponent-id",
                owner_id=2,
                name="Opponent",
                gender="F",
                hp=100.0,
                atk=50.0,
                defense=40.0,
                eva=10.0,
                spd=15.0,
                health=100.0,
                traits=[],
                genetics={},
            )
            trait.on_combat_start(dobu_copy, opponent)
            trait.on_growth_multiplier(dobu_copy, 1.0)

        except Exception as e:
            failed_traits.append((key, str(e)))

    assert not failed_traits, f"Failed traits: {failed_traits}"
