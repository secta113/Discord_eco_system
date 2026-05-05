from unittest.mock import patch

import pytest

from logic.dobumon.core.dob_factory import DobumonFactory
from logic.dobumon.genetics.dob_mutation import MutationEngine
from logic.dobumon.genetics.traits.registry import TraitRegistry


def test_factory_undead_lifespan():
    """不死特性を持つ個体が生成された際、寿命が正しく5倍になることを確認。"""
    with patch(
        "logic.dobumon.genetics.dob_mendel.MendelEngine.resolve_traits", return_value=["undead"]
    ):
        # 通常の初期寿命は 80-120 の間
        dobu = DobumonFactory.create_new(owner_id=1, name="UndeadTest")

        # 不死は lifespan_mod = 5.0 なので、400-600 の間になるはず
        assert "undead" in dobu.traits
        assert 400 <= dobu.lifespan <= 600
        assert dobu.max_lifespan == dobu.lifespan
        assert dobu.illness_rate == 0.0


def test_consumption_mod_accumulation():
    """特性による老化速度倍率の累積を計算。"""
    dobu = DobumonFactory.create_new(owner_id=1, name="ModTest")

    # デフォルト
    dobu.traits = []
    assert dobu.consumption_mod == 1.0

    # 金剛 (hardy): 0.7
    dobu.traits = ["hardy"]
    assert dobu.consumption_mod == 0.7

    # 不死 (undead): 0.2
    dobu.traits = ["undead"]
    assert dobu.consumption_mod == 0.2

    # 金剛 + 不死: 0.7 * 0.2 = 0.14
    dobu.traits = ["hardy", "undead"]
    assert dobu.consumption_mod == 0.14


def test_taboo_red_logic():
    """赤の禁忌による不妊化とステータス補正を検証。"""
    with patch(
        "logic.dobumon.genetics.dob_mendel.MendelEngine.resolve_traits",
        return_value=["forbidden_red"],
    ):
        dobu = DobumonFactory.create_new(owner_id=1, name="RedTest")

        assert "forbidden_red" in dobu.traits
        assert dobu.is_sterile is True
        assert dobu.can_extend_lifespan is False
        # 攻撃力 1.5倍 (初期値は IV 等により変動するが 1.0 よりは大きいはず)
        # 寿命 0.6倍 (80-120 -> 48-72)
        assert 48 <= dobu.lifespan <= 72


def test_antinomy_sterility_reversal():
    """背反特性による不妊化の解除を検証。"""
    # 直接 apply_phenotype_modifiers を呼んで確認
    dobu = DobumonFactory.create_new(owner_id=1, name="AntinomyTest")
    dobu.traits = ["forbidden_red", "antinomy"]
    dobu.is_sterile = False  # 初期化

    MutationEngine.apply_phenotype_modifiers(dobu)

    # forbidden_red は is_sterile=True にするが、antinomy が False に戻すはず
    # registry の順番に依存するが、今の実装では antinomy が後に呼ばれる（または明示的に override する）
    # registry.py の順序: taboo の中で antinomy は forbidden_red より後
    assert dobu.is_sterile is False
    assert dobu.can_extend_lifespan is True
