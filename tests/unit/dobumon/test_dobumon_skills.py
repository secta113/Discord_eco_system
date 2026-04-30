import os

import pytest

from core.handlers import sql_handler
from core.handlers.storage import SQLiteDobumonRepository
from logic.dobumon.core.dob_manager import DobumonManager
from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.training import SKILL_TEMPLATES, get_learnable_skills, get_skill_template


def test_skill_template_integrity():
    """全ての技テンプレートが適切な初期値を持っているか検証"""
    for template in SKILL_TEMPLATES:
        assert template.skill_id
        assert template.default_name
        assert isinstance(template.power, int)
        assert 0 <= template.accuracy <= 100
        assert template.effect_type in ["damage", "buff", "debuff"]


def test_get_skill_template():
    """IDからテンプレートを正しく取得できるか検証"""
    template = get_skill_template("power_hit")
    assert template is not None
    assert template.default_name == "強打"

    assert get_skill_template("non_existent") is None


def test_learnable_skills_logic():
    """ステータスに応じた技の習得判定を検証"""
    # ATK 110, 他 10 の個体 -> ATK 100 以上の技(強打)を覚えられるはず
    stats = {"hp": 100, "atk": 110, "defense": 10, "eva": 10, "spd": 10}
    current_skills = []

    learnable = get_learnable_skills(stats, current_skills)
    template_ids = [t.skill_id for t in learnable]

    assert "power_hit" in template_ids
    # 他の(要求値が高いor属性の)技は含まれないこと
    assert "flare" not in template_ids  # flare は 150 必要


def test_already_learned_skills_filtering():
    """既に覚えている技がリストに出ないことを検証"""
    stats = {"hp": 100, "atk": 200, "defense": 100, "eva": 100, "spd": 100}
    current_skills = [{"template_id": "power_hit", "name": "強打", "is_named": False}]

    learnable = get_learnable_skills(stats, current_skills)
    template_ids = [t.skill_id for t in learnable]

    assert "power_hit" not in template_ids


def test_skill_persistence(tmp_path):
    """技の保存と読み込み（JSONシリアライズ）を検証"""
    db_path = str(tmp_path / "test_skills.db")
    sql_handler.init_db(db_path)
    repo = SQLiteDobumonRepository(db_path)
    manager = DobumonManager(repo)

    dobu = manager.create_dobumon(owner_id=123, name="技丸")
    # 初期スキルを設定
    dobu.skills = [
        {"template_id": "power_hit", "name": "強打", "is_named": False},
        {"template_id": "iron_tail", "name": "鋼の尻尾（命名）", "is_named": True},
    ]
    manager.save_dobumon(dobu)

    # 別レポジトリインスタンスから読み込み
    repo_new = SQLiteDobumonRepository(db_path)
    manager_new = DobumonManager(repo_new)
    retrieved = manager_new.get_dobumon(dobu.dobumon_id)

    assert retrieved is not None
    assert len(retrieved.skills) == 2

    s1 = retrieved.skills[0]
    assert s1["template_id"] == "power_hit"
    assert s1["name"] == "強打"
    assert s1["is_named"] is False

    s2 = retrieved.skills[1]
    assert s2["template_id"] == "iron_tail"
    assert s2["name"] == "鋼の尻尾（命名）"
    assert s2["is_named"] is True
