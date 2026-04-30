import copy
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.dob_battle.dob_calculator import BattleCalculator
from logic.dobumon.dob_shop.dob_items import get_item_by_id
from logic.dobumon.dob_shop.dob_shop_effect_manager import DobumonShopEffectManager
from logic.dobumon.dob_shop.dob_shop_service import DobumonShopService


@pytest.fixture
def base_dobu():
    return Dobumon(
        dobumon_id="test_dobu",
        owner_id=123,
        name="テスト怒武者",
        gender="M",
        hp=100.0,
        atk=100.0,
        defense=100.0,
        eva=100.0,
        spd=100.0,
        health=100.0,
        genetics={"genotype": {"potential": ["D", "r"]}},
        max_lifespan=100.0,
        lifespan=100.0,
    )


class TestDobumonShopEffectManager:
    """DobumonShopEffectManager のテスト"""

    def test_get_breeding_bonuses(self, base_dobu):
        p1 = base_dobu
        p2 = copy.deepcopy(base_dobu)

        # 生贄の刻印を両親に設定
        p1.shop_flags["sacrifice_mark"] = {"iv_bonus": 0.02, "taboo_add": 1}
        p2.shop_flags["sacrifice_mark"] = {"iv_bonus": 0.02, "taboo_add": 1}
        # 特異点の断片
        p1.shop_flags["singularity_fragment"] = {"iv_bonus": 0.05}
        # ミューテーション・ゲノム
        p2.shop_flags["mutation_genome"] = {"chance_delta": 0.1}

        bonuses = DobumonShopEffectManager.get_breeding_bonuses(p1, p2)

        assert bonuses["iv_bonus_base"] == 0.04
        assert bonuses["high_iv_bonus"] == 0.05
        assert bonuses["mutation_chance_delta"] == 0.1
        assert bonuses["taboo_depth_add"] == 2

    def test_get_breeding_bonuses_gender_fix(self, base_dobu):
        p1 = base_dobu
        p2 = copy.deepcopy(base_dobu)

        # ♂固定と♀固定を同時に使った場合
        p1.shop_flags["bad_gender_fix_m"] = {"chance": 0.75, "iv_penalty": -0.02}
        p2.shop_flags["bad_gender_fix_f"] = {"chance": 0.75, "iv_penalty": -0.02}

        bonuses = DobumonShopEffectManager.get_breeding_bonuses(p1, p2)

        assert bonuses["gender_bias_m_chance"] == 0.75
        assert bonuses["gender_bias_f_chance"] == 0.75
        assert bonuses["iv_bonus_base"] == -0.04

    def test_get_training_modifiers(self, base_dobu):
        dobu = base_dobu
        dobu.shop_flags["suicidal_drug"] = {"train_mult": 2.0}
        dobu.shop_flags["muscle_booster"] = {"mult": 1.5}
        dobu.shop_flags["cooling_sheet"] = True

        modifiers = DobumonShopEffectManager.get_training_modifiers(dobu)

        assert modifiers["multiplier"] == 3.0
        assert modifiers["ignore_diminishing_returns"] is True

    def test_get_combat_modifiers(self, base_dobu):
        dobu = base_dobu
        # 忌血の触媒なし
        mods_none = DobumonShopEffectManager.get_combat_modifiers(dobu)
        assert mods_none["atk"] == 1.0

        # 忌血の触媒あり
        dobu.shop_flags["blood_catalyst"] = True
        mods_buff = DobumonShopEffectManager.get_combat_modifiers(dobu)
        assert mods_buff["atk"] == 1.2
        assert mods_buff["defense"] == 1.2

    def test_combat_buff_application(self, base_dobu):
        """忌血の触媒が実際の計算に反映されるか検証"""
        attacker = base_dobu
        defender = copy.deepcopy(base_dobu)

        # 乱数を固定してテストを安定させる
        with (
            patch("random.uniform", return_value=1.0),
            patch("random.random", return_value=0.5),
        ):
            # 1. バフなし状態でのダメージ計算
            res_normal = BattleCalculator.calculate_damage(attacker, defender)
            hit_normal = BattleCalculator.calculate_hit_chance(attacker, defender)

            # 2. バフ付与
            attacker.shop_flags["blood_catalyst"] = True
            res_buffed = BattleCalculator.calculate_damage(attacker, defender)
            hit_buffed = BattleCalculator.calculate_hit_chance(attacker, defender)

            # 3. 検証
            # ダメージ量が増加していること (ATK 1.2x なので、ダメージは約1.44倍弱になるはず)
            assert res_buffed["damage"] > res_normal["damage"]
            # 命中率が向上していること (攻撃側SPDが1.2倍になるため)
            assert hit_buffed > hit_normal


@pytest.mark.asyncio
class TestDobumonShopService:
    """DobumonShopService ハンドラーのテスト"""

    async def test_effect_erasure_logic(self, base_dobu):
        manager = MagicMock()
        service = DobumonShopService(manager)
        item = get_item_by_id("erasure_logic")

        # 初期状態: potential は ['D', 'r']
        assert base_dobu.genetics["genotype"]["potential"] == ["D", "r"]
        initial_lifespan = base_dobu.lifespan

        success, msg = await service._effect_erasure_logic(base_dobu, item)

        assert success is True
        # 遺伝子が rr に書き換わっていること
        assert base_dobu.genetics["genotype"]["potential"] == ["r", "r"]
        # 寿命が減少していること (100 -> 80)
        assert base_dobu.lifespan == initial_lifespan - 20

    async def test_effect_luxury_sweets(self, base_dobu):
        manager = MagicMock()
        service = DobumonShopService(manager)
        item = get_item_by_id("luxury_sweets")

        initial = base_dobu.affection
        await service._effect_luxury_sweets(base_dobu, item)
        assert base_dobu.affection == initial + 3

    async def test_effect_rotten_protein(self, base_dobu):
        manager = MagicMock()
        service = DobumonShopService(manager)
        item = get_item_by_id("rotten_protein")

        base_dobu.hp = 100.0
        base_dobu.health = 100.0
        initial_lifespan = base_dobu.lifespan
        await service._effect_rotten_protein(base_dobu, item)

        assert base_dobu.hp == 105.0
        assert base_dobu.health == 105.0
        assert base_dobu.lifespan == initial_lifespan - 5

    async def test_effect_heavy_geta(self, base_dobu):
        manager = MagicMock()
        service = DobumonShopService(manager)
        item = get_item_by_id("heavy_geta")

        initial_spd = base_dobu.spd
        initial_lifespan = base_dobu.lifespan
        await service._effect_heavy_geta(base_dobu, item)

        assert base_dobu.spd == initial_spd + 20
        assert base_dobu.lifespan == initial_lifespan - 10

    async def test_effect_blank_scroll(self, base_dobu):
        manager = MagicMock()
        service = DobumonShopService(manager)
        item = get_item_by_id("blank_scroll")

        base_dobu.today_train_count = 5
        await service._effect_blank_scroll(base_dobu, item)
        assert base_dobu.today_train_count == 0

    async def test_effect_super_recovery_supple(self, base_dobu):
        manager = MagicMock()
        service = DobumonShopService(manager)
        item = get_item_by_id("super_recovery_supple")

        base_dobu.today_train_count = 5
        initial_lifespan = base_dobu.lifespan
        await service._effect_super_recovery_supple(base_dobu, item)

        assert base_dobu.today_train_count == 2
        assert base_dobu.lifespan == initial_lifespan + 10

    async def test_effect_old_reference_book(self, base_dobu):
        manager = MagicMock()
        service = DobumonShopService(manager)
        item = get_item_by_id("old_reference_book")

        mock_skill = {"template_id": "test_skill", "name": "テスト技", "is_named": False}
        with patch(
            "logic.dobumon.core.dob_factory.DobumonFactory.get_skills_by_rarity",
            return_value=[mock_skill],
        ):
            await service._effect_old_reference_book(base_dobu, item)
            assert any(s["template_id"] == "test_skill" for s in base_dobu.skills)

    async def test_effect_flag_storage_items(self, base_dobu):
        manager = MagicMock()
        service = DobumonShopService(manager)

        # mutation_genome
        item_genome = get_item_by_id("mutation_genome")
        await service._effect_mutation_genome(base_dobu, item_genome)
        assert "mutation_genome" in base_dobu.shop_flags

        # blood_catalyst
        item_catalyst = get_item_by_id("blood_catalyst")
        await service._effect_next_battle_buff(base_dobu, item_catalyst)
        assert "blood_catalyst" in base_dobu.shop_flags

    async def test_effect_gender_reverse(self, base_dobu):
        manager = MagicMock()
        service = DobumonShopService(manager)
        item = get_item_by_id("gender_reverse")

        base_dobu.gender = "M"
        success, msg = await service._effect_gender_reverse(base_dobu, item)
        assert success is True
        assert base_dobu.gender == "F"

    async def test_effect_gender_reverse_forbidden(self, base_dobu):
        manager = MagicMock()
        service = DobumonShopService(manager)
        item = get_item_by_id("gender_reverse")

        base_dobu.gender = "M"
        base_dobu.traits = ["forbidden_red"]
        success, msg = await service._effect_gender_reverse(base_dobu, item)
        assert success is False
        assert base_dobu.gender == "M"

    async def test_effect_next_breed_gender_fix(self, base_dobu):
        manager = MagicMock()
        service = DobumonShopService(manager)
        item = get_item_by_id("bad_gender_fix_m")

        success, msg = await service._effect_next_breed_gender_fix(base_dobu, item)
        assert success is True
        assert "bad_gender_fix_m" in base_dobu.shop_flags

    async def test_effect_next_breed_gender_fix_forbidden(self, base_dobu):
        manager = MagicMock()
        service = DobumonShopService(manager)
        item = get_item_by_id("bad_gender_fix_f")

        base_dobu.genetics["has_forbidden_blue"] = True
        success, msg = await service._effect_next_breed_gender_fix(base_dobu, item)
        assert success is False
        assert "bad_gender_fix_f" not in base_dobu.shop_flags

    async def test_execute_purchase_flow(self, base_dobu):
        """execute_purchase の全体フローテスト"""
        manager = MagicMock()
        manager.get_dobumon.return_value = base_dobu
        service = DobumonShopService(manager)

        user_id = 123
        item_id = "luxury_sweets"

        with (
            patch("core.economy.wallet.load_balance", return_value=100000),
            patch(
                "logic.economy.provider.EconomyProvider.escrow", return_value=True
            ) as mock_escrow,
        ):
            success, msg = await service.execute_purchase(user_id, item_id, base_dobu.dobumon_id)

            assert success is True
            mock_escrow.assert_called_once()
            manager.save_dobumon.assert_called_once_with(base_dobu)
            assert base_dobu.affection > 0
