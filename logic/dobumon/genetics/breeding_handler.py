from typing import Dict

from logic.dobumon.core.dob_exceptions import DobumonError, DobumonNotFoundError
from logic.dobumon.core.dob_logger import DobumonLogger
from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.genetics.dob_breeders import BreedingFactory


class BreedingHandler:
    """
    怒武者の交配と遺伝を管理するハンドラー。
    """

    def __init__(self, manager):
        self.manager = manager

    def breed_dobumon(self, parent1_id: str, parent2_id: str, child_name: str) -> Dict:
        """
        2体の怒武者を交配させ、新しい個体を生成します。
        親は引退間近になります。
        """
        p1 = self.manager.get_dobumon(parent1_id)
        p2 = self.manager.get_dobumon(parent2_id)

        if not p1 or not p2 or not p1.is_alive or not p2.is_alive:
            raise DobumonNotFoundError("親となる個体が見つからないか、生存していません。")

        if p1.dobumon_id == p2.dobumon_id:
            raise DobumonError("同一の個体同士で交配することはできません。")

        if p1.is_sterile or p2.is_sterile:
            raise DobumonError("生殖能力のない個体が選択されています（薔薇個体など）。")

        # 1. 配合実行 (GAエンジン)
        breeder = BreedingFactory.get_breeder(p1, p2)
        child = breeder.breed(p1, p2, child_name)

        # 1.5 加齢による IV 減衰補正の適用
        inheritance_mod = p1.inheritance_multiplier * p2.inheritance_multiplier
        if inheritance_mod < 1.0:
            for stat in child.iv:
                child.iv[stat] = round(child.iv[stat] * inheritance_mod, 2)
            # 実数値も再計算（簡易的に）
            child.hp = int(child.hp * inheritance_mod)
            child.atk = int(child.atk * inheritance_mod)
            child.defense = int(child.defense * inheritance_mod)
            child.eva = int(child.eva * inheritance_mod)
            child.spd = int(child.spd * inheritance_mod)

        # 2. 親の寿命を大幅に削る (定数 20 消費)
        p1.lifespan = max(1, p1.lifespan - 20)
        p2.lifespan = max(1, p2.lifespan - 20)

        # 2.5 ショップアイテム効果の消費
        for parent in [p1, p2]:
            for flag in [
                "sacrifice_mark",
                "mutation_genome",
                "singularity_fragment",
                "bad_gender_fix_m",
                "bad_gender_fix_f",
            ]:
                if flag in parent.shop_flags:
                    del parent.shop_flags[flag]

        # 3. 永続化
        self.manager.save_dobumon(p1)
        self.manager.save_dobumon(p2)
        self.manager.save_dobumon(child)

        DobumonLogger.genetics(child, context="Breeding", p1_name=p1.name, p2_name=p2.name)

        return {
            "success": True,
            "child": child,
            "p1_name": p1.name,
            "p2_name": p2.name,
        }
