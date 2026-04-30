import random
from dataclasses import dataclass
from typing import Dict, List, Optional

from core.utils.logger import Logger
from logic.dobumon.core.dob_exceptions import DobumonError
from logic.dobumon.core.dob_models import Dobumon


@dataclass
class SkillTemplate:
    skill_id: str
    default_name: str
    description: str
    required_stat: str
    threshold: int
    power: int = 0
    accuracy: int = 100
    effect_type: str = "damage"  # damage, buff, debuff


# プロトタイプ用の技リスト
SKILL_TEMPLATES = [
    SkillTemplate(
        "power_hit", "強打", "ATKに依存した強力な一撃", "atk", 100, power=80, accuracy=90
    ),
    SkillTemplate(
        "quick_step", "加速装置", "SPDを一時的に上昇させる", "spd", 50, effect_type="buff"
    ),
    SkillTemplate(
        "iron_wall", "鉄壁", "DEFを大幅に高めて耐える", "defense", 80, effect_type="buff"
    ),
    SkillTemplate("flare", "フレア", "高熱を叩きつける", "atk", 150, power=100, accuracy=85),
    SkillTemplate(
        "aqua_jet", "アクアジェット", "水流で押し流す", "atk", 120, power=70, accuracy=100
    ),
    SkillTemplate(
        "leaf_blade", "リーフブレード", "鋭い葉で斬りつける", "atk", 130, power=90, accuracy=95
    ),
]


def get_skill_template(template_id: str) -> Optional[SkillTemplate]:
    """
    IDからテンプレートを取得します。
    """
    for t in SKILL_TEMPLATES:
        if t.skill_id == template_id:
            return t
    return None


def get_learnable_skills(
    dobu_stats: Dict[str, int], current_skills: List[Dict]
) -> List[SkillTemplate]:
    """
    現在のステータスで習得可能な技を返します（未習得のもののみ）。
    """
    learned_ids = [s.get("template_id") for s in current_skills]
    learnable = []
    for template in SKILL_TEMPLATES:
        if template.skill_id not in learned_ids:
            if dobu_stats.get(template.required_stat, 0) >= template.threshold:
                learnable.append(template)
    return learnable


def check_and_learn_skill(dobu: Dobumon) -> Optional[str]:
    """
    ステータスに基づき、新しい技を習得できるかチェックします。
    """
    if len(dobu.skills) >= 4:
        return None

    stats = {
        "hp": dobu.hp,
        "atk": dobu.atk,
        "defense": dobu.defense,
        "eva": dobu.eva,
        "spd": dobu.spd,
    }
    learnable = get_learnable_skills(stats, dobu.skills)

    if not learnable:
        return None

    # 習得 (プロトタイプなので簡易的に20%の確率で習得)
    if random.random() < 0.20:
        new_skill = random.choice(learnable)
        dobu.skills.append(
            {
                "template_id": new_skill.skill_id,
                "name": new_skill.default_name,
                "is_named": False,
            }
        )
        Logger.info("Dobumon", f"{dobu.name} learned a new skill: {new_skill.default_name}")
        return new_skill.default_name
    return None


def rename_skill(dobu: Dobumon, skill_index: int, new_name: str):
    """
    技の名前を変更します。一度のみ変更可能です。
    """
    if skill_index >= len(dobu.skills):
        raise DobumonError("対象の技が見つかりません。")

    skill = dobu.skills[skill_index]
    if skill.get("is_named"):
        raise DobumonError("この技は既に命名済みです。変更はできません。")

    skill["name"] = new_name
    skill["is_named"] = True
    return True, "命名が完了しました。"
