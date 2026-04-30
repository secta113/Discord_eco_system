import random
import uuid
from typing import Dict, List

from logic.dobumon.core.dob_logger import DobumonLogger
from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.training.dob_skills import SKILL_TEMPLATES


class DobumonFactory:
    """
    怒武者（ドブモン）の生成を専門に扱うファクトリクラス。
    購入、野生、交配など、異なる文脈での個体生成ロジックを集約します。
    """

    @staticmethod
    def create_new(
        owner_id: int,
        name: str,
        source: str = "buyer",
        gender: str = None,
        attribute: str = None,
        custom_iv: Dict[str, float] = None,
        force_mutation: bool = False,
    ) -> Dobumon:
        """
        新規に怒武者を生成します（購入、ガチャ等）。
        """
        from logic.dobumon.genetics.dob_mendel import MendelEngine

        dobumon_id = str(uuid.uuid4())
        if gender is None:
            gender = random.choice(["M", "F"])

        # ベースステータス
        base_hp = 100
        base_atk = 50
        base_defense = 40
        base_eva = 10
        base_spd = 15

        # IV (個体値) の生成
        if custom_iv:
            iv = custom_iv
        else:
            if source == "buyer":
                iv_range = (0.9, 1.1)
            elif source == "gacha":
                iv_range = (1.0, 1.4)
            else:
                iv_range = (0.8, 1.2)

            iv = {
                "hp": round(random.uniform(*iv_range), 2),
                "atk": round(random.uniform(*iv_range), 2),
                "defense": round(random.uniform(*iv_range), 2),
                "eva": round(random.uniform(*iv_range), 2),
                "spd": round(random.uniform(*iv_range), 2),
            }

        # 遺伝情報の初期化
        genotype = MendelEngine.get_initial_genotype()

        # 強制突然変異 (ショップの特典など)
        if force_mutation:
            # growth 遺伝子を希少種に変異させる
            from logic.dobumon.genetics.dob_genetics_constants import GeneticConstants

            rare_alleles = [
                a
                for a in GeneticConstants.TRAIT_EFFECTS
                if a not in ["early", "late", "hardy", "frail", "stable", "burst", "aesthetic"]
                and "forbidden" not in a
            ]
            if rare_alleles:
                genotype["growth"] = [random.choice(rare_alleles), "r"]

        traits = MendelEngine.resolve_traits(genotype, {})

        if attribute is None:
            attribute = random.choice(["fire", "water", "grass"])

        dobu = Dobumon(
            dobumon_id=dobumon_id,
            owner_id=owner_id,
            name=name,
            gender=gender,
            hp=int(base_hp * iv["hp"]),
            atk=int(base_atk * iv["atk"]),
            defense=int(base_defense * iv["defense"]),
            eva=int(base_eva * iv["eva"]),
            spd=int(base_spd * iv["spd"]),
            health=int(base_hp * iv["hp"]),  # フルHPで初期化
            iv=iv,
            attribute=attribute,
            lifespan=random.randint(80, 120),
            max_lifespan=0,  # 後でセット
            generation=1,
            genetics={"genotype": genotype},
            traits=traits,
            lineage=[],
        )
        dobu.max_lifespan = dobu.lifespan  # 確定した寿命をコピー

        DobumonLogger.genetics(dobu, context="Factory")
        return dobu

    @staticmethod
    def create_wild(
        stats_config: Dict[str, List[int]],
        attribute: str = None,
        forbidden_depth: int = 0,
    ) -> Dobumon:
        """
        野生の怒武者を生成します。指定されたステータス範囲と禁忌深度を適用します。
        """
        from logic.dobumon.genetics.dob_mendel import MendelEngine

        dobumon_id = f"wild-{uuid.uuid4()}"

        def get_stat(key):
            r = stats_config.get(key, [10, 20])
            return random.randint(r[0], r[1])

        genotype = MendelEngine.get_initial_genotype()
        traits = MendelEngine.resolve_traits(genotype, {})

        if attribute is None:
            attribute = random.choice(["fire", "water", "grass"])

        dobu = Dobumon(
            dobumon_id=dobumon_id,
            owner_id=0,
            name=random.choice(["野生のドブ", "凶暴なドブ", "はぐれドブ", "飢えたドブ"]),
            gender=random.choice(["M", "F"]),
            hp=get_stat("hp"),
            atk=get_stat("atk"),
            defense=get_stat("defense"),
            eva=get_stat("eva"),
            spd=get_stat("spd"),
            health=0,  # 下でセット
            attribute=attribute,
            lifespan=999,
            max_lifespan=999,
            generation=1,
            genetics={"genotype": genotype, "forbidden_depth": forbidden_depth},
            traits=traits,
            lineage=[],
        )
        dobu.health = dobu.hp
        return dobu

    @staticmethod
    def get_skills_by_rarity(attribute: str = "none") -> List[Dict]:
        """属性に応じた技リストを（現在は全リストから）返します。"""
        return [
            {"template_id": t.skill_id, "name": t.default_name, "is_named": False}
            for t in SKILL_TEMPLATES
        ]

    @staticmethod
    def generate_iv_hints(iv: Dict[str, float]) -> str:
        """
        IVの値に基づいて、抽象的なヒントテキストを生成します。
        """
        avg_iv = sum(iv.values()) / len(iv)

        if avg_iv >= 1.45:
            base_hint = "神々しいまでの覇気を放っている……！"
        elif avg_iv >= 1.35:
            base_hint = "恐るべき潜在能力を秘めているようだ。"
        elif avg_iv >= 1.25:
            base_hint = "非常に優れた素質を感じる。"
        elif avg_iv >= 1.15:
            base_hint = "なかなかの逸材かもしれない。"
        elif avg_iv >= 1.05:
            base_hint = "標準よりも力強さを感じる。"
        elif avg_iv >= 0.95:
            base_hint = "平均的な能力を持っているようだ。"
        else:
            base_hint = "少し頼りないが、伸び代はあるだろう。"

        # 特筆すべきステータスの抽出
        best_stat = max(iv, key=iv.get)
        if iv[best_stat] >= 1.4:
            stat_names = {
                "hp": "生命力",
                "atk": "攻撃性",
                "defense": "頑強さ",
                "eva": "身のこなし",
                "spd": "瞬発力",
            }
            base_hint += f"\n特に**{stat_names[best_stat]}**に関しては、目を見張るものがある。"

        return base_hint
