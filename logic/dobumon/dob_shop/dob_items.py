from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class ShopItem:
    item_id: str
    name: str
    description: str
    price: int
    category: str  # 'consumable' (immediate) or 'reservation' (next action)
    effect_type: str  # e.g., 'lifespan', 'breed_iv', 'train_mult'
    effect_value: Any


@dataclass
class Shop:
    shop_id: str
    name: str
    description: str
    items: List[ShopItem]
    is_vip: bool = False


# アイテム定義
ITEMS = {
    # 闇の露店
    "sacrifice_mark": ShopItem(
        "sacrifice_mark",
        "生贄の刻印",
        "次回の交配時、禁忌震度を+1し、全ステータスの継承IVに+0.02のボーナスを付与する。",
        150000,
        "reservation",
        "next_breed_iv",
        {"taboo_add": 1, "iv_bonus": 0.02},
    ),
    "blood_catalyst": ShopItem(
        "blood_catalyst",
        "忌血の触媒",
        "次回の戦闘時、自身の全ステータスを+20%するバフを付与する。",
        80000,
        "reservation",
        "next_battle_buff",
        {"stat_bonus": 0.2},
    ),
    "suicidal_drug": ShopItem(
        "suicidal_drug",
        "自滅の劇薬",
        "寿命を-15するが、次回のトレーニング上昇量を3.0倍にする。",
        120000,
        "mixed",  # lifespan is immediate, train is reservation
        "suicidal_training",
        {"lifespan_delta": -15, "train_mult": 3.0},
    ),
    # ドブ屋
    "rotten_protein": ShopItem(
        "rotten_protein",
        "腐ったプロテイン",
        "最大HPを+5するが、寿命が-5される。",
        150000,
        "consumable",
        "hp_max_boost_damage",
        {"hp_bonus": 5, "lifespan_delta": -5},
    ),
    "heavy_geta": ShopItem(
        "heavy_geta",
        "重すぎる鉄下駄",
        "即座に素早さを+20するが、寿命を-10する。",
        200000,
        "consumable",
        "stat_boost_damage",
        {"stat": "spd", "value": 20, "lifespan_delta": -10},
    ),
    "old_reference_book": ShopItem(
        "old_reference_book",
        "使い古しの参考書",
        "ランダムにスキルを一つ習得する。既に習得済みの場合は効果がない。",
        100000,
        "consumable",
        "learn_skill",
        None,
    ),
    "bad_gender_fix_m": ShopItem(
        "bad_gender_fix_m",
        "粗悪な性別固定カプセル♂",
        "次なる生命の形を♂へと歪める劇薬。運命を曲げる代償として、受け継がれる遺伝子に小さな傷跡を残す。",
        100000,
        "reservation",
        "next_breed_gender_fix",
        {"gender_bias": "M", "chance": 0.75, "iv_penalty": -0.02},
    ),
    "bad_gender_fix_f": ShopItem(
        "bad_gender_fix_f",
        "粗悪な性別固定カプセル♀",
        "次なる生命の形を♀へと歪める劇薬。運命を曲げる代償として、受け継がれる遺伝子に小さな傷跡を残す。",
        100000,
        "reservation",
        "next_breed_gender_fix",
        {"gender_bias": "F", "chance": 0.75, "iv_penalty": -0.02},
    ),
    # 町の雑貨屋
    "luxury_sweets": ShopItem(
        "luxury_sweets",
        "高級菓子折り",
        "懐き度を即座に+3する。",
        10000,
        "consumable",
        "affection_boost",
        {"value": 3},
    ),
    "blank_scroll": ShopItem(
        "blank_scroll",
        "無地の巻物",
        "本日のトレーニング回数をリセット（現在値を0に）する。",
        100000,
        "consumable",
        "reset_train_count",
        None,
    ),
    # マッスルランデブー
    "muscle_booster": ShopItem(
        "muscle_booster",
        "筋繊維ブースター",
        "以降5回分のトレーニング上昇量を1.1倍（整腸効果）にする。",
        120000,
        "reservation",
        "training_buff_5",
        {"mult": 1.1, "count": 5},
    ),
    "cooling_sheet": ShopItem(
        "cooling_sheet",
        "冷却シップ",
        "次回のトレーニング時、ステータスが高くても成長が鈍らなくなる。",
        80000,
        "reservation",
        "ignore_diminishing_returns",
        None,
    ),
    "super_recovery_supple": ShopItem(
        "super_recovery_supple",
        "超回復サプリ",
        "即座に疲労をリセットし、寿命を+10する。",
        150000,
        "consumable",
        "lifespan_boost",
        {"value": 10},
    ),
    # Gengularity
    "singularity_fragment": ShopItem(
        "singularity_fragment",
        "特異点の断片",
        "次回の交配時、両親の最も高いIVを、本来の継承計算後にさらに+0.05上昇させる。",
        750000,
        "reservation",
        "next_breed_high_iv_bonus",
        {"iv_bonus": 0.05},
    ),
    "mutation_genome": ShopItem(
        "mutation_genome",
        "ミューテーション・ゲノム",
        "次回の交配時、突然変異（Mutation）の発生確率を+20%する。",
        450000,
        "reservation",
        "next_mutation_boost",
        {"chance_delta": 0.20},
    ),
    "erasure_logic": ShopItem(
        "erasure_logic",
        "理の崩壊",
        "怒武者の潜在能力(potential)を『爆発(Burst)』に書き換える。寿命-20。",
        1500000,
        "consumable",
        "potential_overwrite",
        {"lifespan_delta": -20},
    ),
    "gender_reverse": ShopItem(
        "gender_reverse",
        "性別反転カプセル",
        "肉体の理を書き換え、新たな性別へと生まれ変わらせる神秘の秘薬。だが、深き禁忌の血脈を持つ者には決して届かない。",
        500000,
        "consumable",
        "gender_reverse",
        None,
    ),
}

SHOPS = [
    Shop(
        "grocery",
        "町の雑貨屋",
        "日用品からドブモン用の嗜好品まで揃う、街一番の商店。",
        [ITEMS["luxury_sweets"], ITEMS["blank_scroll"]],
    ),
    Shop(
        "dark_stall",
        "闇の露店",
        "禁忌に触れる怪しい品々を扱う。効果は絶大だが代償も大きい。",
        [ITEMS["sacrifice_mark"], ITEMS["blood_catalyst"], ITEMS["suicidal_drug"]],
    ),
    Shop(
        "dobu_ya",
        "ドブ屋",
        "ドブモン専用の育成用品店。安価だが副作用があるものも多い。",
        [
            ITEMS["rotten_protein"],
            ITEMS["heavy_geta"],
            ITEMS["old_reference_book"],
            ITEMS["bad_gender_fix_m"],
            ITEMS["bad_gender_fix_f"],
        ],
    ),
    Shop(
        "muscle",
        "マッスルランデブー",
        "効率的なトレーニングを追求する者たちのための専門店。",
        [ITEMS["muscle_booster"], ITEMS["cooling_sheet"], ITEMS["super_recovery_supple"]],
    ),
    Shop(
        "gengularity",
        "Gengularity",
        "特定の者のみが入場を許される、遺伝子の深淵に触れる店。",
        [
            ITEMS["singularity_fragment"],
            ITEMS["mutation_genome"],
            ITEMS["erasure_logic"],
            ITEMS["gender_reverse"],
        ],
        is_vip=True,
    ),
]


def get_shop_by_id(shop_id: str) -> Optional[Shop]:
    for shop in SHOPS:
        if shop.shop_id == shop_id:
            return shop
    return None


def get_item_by_id(item_id: str) -> Optional[ShopItem]:
    return ITEMS.get(item_id)
