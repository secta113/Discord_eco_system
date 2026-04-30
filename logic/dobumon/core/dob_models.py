from dataclasses import dataclass, field
from typing import Any, Dict, List

from logic.dobumon.genetics.dob_taboo import TabooLogic


@dataclass
class Dobumon:
    """
    怒武者（ドブモン）の個体データを表すクラス。
    """

    dobumon_id: str
    owner_id: int
    name: str
    gender: str
    hp: float  # 最大HP（訓練で育てるステータス値）
    atk: float
    defense: float
    eva: float
    spd: float
    health: float = 0.0  # 現在HP（0.0 = 未設定、バトル後に更新される。0.0 の場合は hp と同値扱い）
    skills: List[Dict] = field(default_factory=list)
    iv: Dict[str, float] = field(default_factory=dict)
    lifespan: float = 100.0
    is_alive: bool = True
    attribute: str = ""
    affection: int = 0
    # 遺伝・世代情報
    generation: int = 1
    genetics: Dict[str, Any] = field(default_factory=dict)  # 詳細な遺伝型データ (メンデルの法則用)
    lineage: List[str] = field(default_factory=list)  # 親・祖先のIDリスト（近親交配チェック用）
    traits: List[str] = field(default_factory=list)  # 発現している特性名

    # 特殊フラグ・レート
    is_sterile: bool = False
    illness_rate: float = 0.01  # 基本の病気率
    can_extend_lifespan: bool = True  # 延命アイテムが使えるか
    max_lifespan: float = 100.0  # 誕生時/受領時の初期寿命 (100%基準)

    # 戦績
    win_count: int = 0
    rank: int = 0

    # 育成管理
    last_train_date: str = "1970-01-01"
    today_train_count: int = 0
    today_wild_battle_count: int = 0
    today_affection_gain: int = 0
    today_massage_count: int = 0
    is_sold: bool = False
    shop_flags: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    @property
    def life_stage(self) -> str:
        """寿命の残り割合に基づいたライフステージを返します。"""
        # 初期寿命（max_lifespan）を基準とした相対値でステージ判定を行う
        ratio = self.lifespan / self.max_lifespan if self.max_lifespan > 0 else 0

        if ratio > 0.8:
            return "young"
        elif ratio >= 0.3:
            return "prime"
        elif ratio >= 0.1:
            return "senior"
        else:
            return "twilight"

    @property
    def growth_multiplier(self) -> float:
        """ステージに応じたトレーニング成長倍率"""
        multipliers = {
            "young": 1.5,
            "prime": 1.0,
            "senior": 0.5,
            "twilight": 0.1,
        }
        base = multipliers.get(self.life_stage, 1.0)
        return TabooLogic.get_growth_multiplier(self, base)

    @property
    def battle_multiplier(self) -> float:
        """ステージに応じた戦闘能力倍率"""
        multipliers = {
            "young": 0.8,
            "prime": 1.0,
            "senior": 1.0,
            "twilight": 0.7,
        }
        return multipliers.get(self.life_stage, 1.0)

    @property
    def inheritance_multiplier(self) -> float:
        """ステージに応じた子への遺伝ポテンシャル継承倍率"""
        multipliers = {
            "young": 1.0,  # 幼年期も交配可能とする
            "prime": 1.0,
            "senior": 0.8,
            "twilight": 0.5,
        }
        return multipliers.get(self.life_stage, 1.0)

    def die(self):
        """死亡フラグを立てる（論理削除）"""
        self.is_alive = False
        self.health = 0.0

    def revive(self):
        """生存状態に戻す"""
        self.is_alive = True
        self.is_sold = False

    def sell(self):
        """売却処理（論理削除）"""
        self.is_alive = False
        self.is_sold = True
        self.health = 0.0

    @property
    def consumption_mod(self) -> float:
        """
        寿命消費および疲労蓄積の倍率。
        遺伝、特性、懐き度によって変動します。
        """
        mod = self.genetics.get("consumption_mod", 1.0)

        # 1. 禁忌深度による加速 (TabooLogic に委譲)
        mod = TabooLogic.apply_status_modifiers(self, mod)

        # 2. 特性による補正
        if "forbidden_blue" in self.traits:
            mod *= 2.0
        if "hardy" in self.traits:
            mod *= 0.7
        if "frail" in self.traits:
            mod *= 1.5

        # 3. 懐き度による老化速度の緩和
        if self.affection >= 100:
            mod *= 0.85
        elif self.affection >= 50:
            mod *= 0.95

        return round(mod, 3)

    def to_dict(self) -> Dict:
        """保存用辞書への変換"""
        return {
            "dobumon_id": self.dobumon_id,
            "owner_id": self.owner_id,
            "name": self.name,
            "gender": self.gender,
            "hp": self.hp,
            "atk": self.atk,
            "defense": self.defense,
            "eva": self.eva,
            "spd": self.spd,
            "health": self.health,
            "skills": self.skills,
            "iv": self.iv,
            "lifespan": self.lifespan,
            "is_alive": self.is_alive,
            "attribute": self.attribute,
            "affection": self.affection,
            "genetics": self.genetics,
            "lineage": self.lineage,
            "traits": self.traits,
            "win_count": self.win_count,
            "rank": self.rank,
            "generation": self.generation,
            "is_sterile": self.is_sterile,
            "illness_rate": self.illness_rate,
            "can_extend_lifespan": self.can_extend_lifespan,
            "max_lifespan": self.max_lifespan,
            "last_train_date": self.last_train_date,
            "today_train_count": self.today_train_count,
            "today_wild_battle_count": self.today_wild_battle_count,
            "today_affection_gain": self.today_affection_gain,
            "today_massage_count": self.today_massage_count,
            "is_sold": self.is_sold,
            "shop_flags": self.shop_flags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
