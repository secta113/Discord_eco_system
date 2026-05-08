import pytest

from logic.dobumon.core.dob_factory import DobumonFactory
from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.genetics.dob_mendel import MendelEngine
from logic.dobumon.genetics.dob_mutation import MutationEngine


def test_undead_lifespan_reflection():
    """不死特性（undead）が寿命に正しく反映されることを確認（回帰テスト）"""
    # 1. 不死特性を持つ個体を作成
    genotype = MendelEngine.get_initial_genotype()
    # 手動で vitality スロットを undead に設定
    genotype["vitality"] = ["undead", "undead"]

    traits = MendelEngine.resolve_traits(genotype, {}, gender="M")
    assert "undead" in traits

    dobu = Dobumon(
        dobumon_id="test-undead",
        owner_id=12345,
        name="TestUndead",
        gender="M",
        hp=100,
        atk=50,
        defense=40,
        eva=10,
        spd=15,
        health=100,
        iv={},
        attribute="fire",
        lifespan=100,
        max_lifespan=100,
        traits=traits,
        genetics={"genotype": genotype},
    )

    # 2. 補正適用
    MutationEngine.apply_phenotype_modifiers(dobu)

    # 3. 寿命が5倍（100 -> 500）になっているか確認
    assert dobu.lifespan == 500
    assert dobu.max_lifespan == 500


def test_antinomy_sterility_override():
    """背反特性（antinomy）が禁忌による不妊を正しく解除することを確認（回帰テスト）"""
    # 1. 背反と禁忌（赤）の両方が発現する条件を作成
    genotype = MendelEngine.get_initial_genotype()
    genotype["potential"] = ["antinomy", "antinomy"]

    # 禁忌情報を付与
    genetics_meta = {"has_forbidden_red": True}

    # 解決順序が重要: antinomy が最後に来る必要がある
    traits = MendelEngine.resolve_traits(genotype, genetics_meta, gender="M")
    assert "antinomy" in traits
    assert "forbidden_red" in traits

    dobu = Dobumon(
        dobumon_id="test-antinomy",
        owner_id=12345,
        name="TestAntinomy",
        gender="M",
        hp=100,
        atk=50,
        defense=40,
        eva=10,
        spd=15,
        health=100,
        iv={},
        attribute="fire",
        lifespan=100,
        max_lifespan=100,
        traits=traits,
        genetics={"genotype": genotype, "has_forbidden_red": True},
    )

    # 2. 補正適用
    MutationEngine.apply_phenotype_modifiers(dobu)

    # 3. 不妊フラグが False であることを確認（antinomy の効果）
    assert dobu.is_sterile is False


def test_health_sync_on_factory_creation():
    """ファクトリ生成時に HP 補正後の Health が HP に同期されていることを確認（回帰テスト）"""
    # 合成獣（chimera）は HP 2.5倍。ベース 100 なら 250 になるはず
    # create_new を使用して生成
    # MutationEngine.apply_mutation で強制的に chimera を付与するのはランダム性が高いので
    # MendelEngine をモックするか、あるいは特定の IV を指定して結果を予測する

    # シンプルに Chimera が出るように設定
    custom_iv = {"hp": 1.0, "atk": 1.0, "defense": 1.0, "eva": 1.0, "spd": 1.0}

    # Factory.create_new 内部で MutationEngine.apply_mutation が呼ばれるのを期待するか
    # あるいは traits を強制的に注入する

    # ここでは MutationEngine.apply_phenotype_modifiers の直後の同期を確認する
    dobu = Dobumon(
        dobumon_id="test-sync",
        owner_id=12345,
        name="TestSync",
        gender="M",
        hp=100,
        health=100,
        atk=50,
        defense=40,
        eva=10,
        spd=15,
        traits=["chimera"],  # HP 2.5倍
        genetics={},
    )

    # 補正適用
    MutationEngine.apply_phenotype_modifiers(dobu)

    # HP は 250 になっているはず
    assert dobu.hp == 250

    # 以前のバグでは health は 100 のままだった。同期されていることを確認
    # 注: MutationEngine 内部ではなく Factory 側で同期しているため、Factory 経由でテストする

    # 実際は DobumonFactory.create_new の内部で同期が行われる
    # モックを使用して Chimera を持たせた個体を生成
    import random
    from unittest.mock import patch

    with patch(
        "logic.dobumon.genetics.dob_mendel.MendelEngine.resolve_traits", return_value=["chimera"]
    ):
        dobu_factory = DobumonFactory.create_new(
            owner_id=12345, name="FactorySyncTest", custom_iv=custom_iv
        )

        assert dobu_factory.hp == 250
        assert dobu_factory.health == 250
        assert "chimera" in dobu_factory.traits
