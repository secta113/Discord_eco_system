from typing import Any, Dict, List

# --- Genetic Data ---

# 遺伝子の属性定義 [優性アレル: 表現型, 劣性アレル: 表現型]。
TRAIT_GENES: Dict[str, Dict[str, str]] = {
    "growth": {"D": "early", "r": "late", "desc": "成長曲線判定用 locus"},
    "vitality": {"D": "hardy", "r": "frail", "desc": "健康状態判定用 locus"},
    "potential": {"D": "stable", "r": "burst", "desc": "潜在能力の爆発力判定用 locus"},
    "body": {"D": "normal", "r": "aesthetic", "desc": "肉体特徴判定用 locus"},
}

# 各形質（表現型）の具体的効果の定義
TRAIT_EFFECTS: Dict[str, Dict[str, Any]] = {
    "early": {
        "desc": "早熟: 初期値が高いが、後半の伸びが鈍い",
        "hp_mod": 1.2,
        "growth_mod": 0.8,
    },
    "late": {
        "desc": "晩成: 初期値は低いが、限界突破しやすい",
        "hp_mod": 0.8,
        "growth_mod": 1.5,
    },
    "hardy": {
        "desc": "金剛: 病気になりにくく、タフである",
        "illness_mod": 0.5,
        "lifespan_mod": 1.2,
    },
    "frail": {
        "desc": "繊細: 病気になりやすいが、感性が鋭い",
        "illness_mod": 2.0,
        "eva_mod": 1.2,
    },
    "stable": {"desc": "安定: ステータスの振れ幅が小さい", "variation_range": (0.95, 1.05)},
    "burst": {
        "desc": "爆発: 突然変異や大成功が起きやすい",
        "mutation_mod": 2.0,
        "great_success_mod": 2.0,
    },
    "aesthetic": {
        "desc": "美形: 端麗な容姿。回避率がわずかに高い",
        "eva_mod": 1.05,
    },
    # --- 禁忌 (同性間配合による血の不均衡) ---
    "forbidden_red": {
        "desc": "赤の禁忌: オスの血が濃すぎることによる暴走。圧倒的攻撃力を持つが、不妊となり短命化する",
        "atk_mod": 1.5,
        "spd_mod": 1.2,
        "lifespan_mod": 0.6,
    },
    "forbidden_blue": {
        "desc": "青の禁忌: メスの血が薄すぎることによる神秘。感性が鋭く、生命力が高いが、極めて短命となる",
        "hp_mod": 1.2,
        "eva_mod": 1.2,
        "lifespan_mod": 0.5,
    },
    # --- 希少突然変異 (Mutation Traits) ---
    "gold_horn": {
        "desc": "金角: 威厳により勝利報酬が1.1倍に増加する (+物理防御)",
        "def_mod": 1.2,
        "reward_mod": 1.1,
    },
    "red_back": {"desc": "赤背: 激しい闘争本能により攻撃力が大幅に上昇する", "atk_mod": 1.3},
    "odd_eye": {"desc": "妖眼: 異なる次元を視る瞳。回避率と命中率が向上する", "eva_mod": 1.3},
    "blue_blood": {
        "desc": "青血: 高貴なエイリアン・ブラッド。HPと生命力が極めて高い",
        "hp_mod": 1.3,
        "illness_mod": 0.5,
    },
    # --- 存在の突然変異 (Conceptual Mutations) ---
    "unlimited": {
        "desc": "無限: 成長の限界を超越し、育成時のステータス減衰を無視する",
        "growth_mod": 1.5,
    },
    "parasitic": {
        "desc": "捕食: 普段ステータスが伸びないが戦闘時等で飛躍的に成長・報酬を得る",
    },
    "undead": {
        "desc": "不死: 死の概念がない。寿命が極めて長く病気にならず、敗北ロストを無効化する",
        "lifespan_mod": 5.0,
        "illness_mod": 0.0,
    },
    "crystalized": {
        "desc": "結晶化: 硬いが脆いガラスの盾。病気にならないがHPが極端に低い",
        "def_mod": 2.0,
        "hp_mod": 0.5,
        "illness_mod": 0.0,
    },
    "chimera": {
        "desc": "合成獣: 無尽蔵の体力を持つが、拒絶反応により常に重病に苛まれる",
        "hp_mod": 2.5,
        "illness_mod": 3.0,
    },
    "glass_blade": {
        "desc": "硝子の刃: HPと防御力が半減する代わりに、攻撃力と速度が2.5倍になる狂気の刃",
        "hp_mod": 0.5,
        "def_mod": 0.5,
        "atk_mod": 2.5,
        "spd_mod": 2.5,
    },
    "supernova": {
        "desc": "超新星: 個体値の振れ幅が最大となり、次世代の突然変異率を極限まで高める",
        "mutation_mod": 5.0,
        "variation_range": (0.5, 2.5),
    },
    "singularity": {
        "desc": "特異点: 絶対不変の完成形。両親の優れた能力を無欠で引き継ぎ、その形を永劫に保つ究極の個体。子に必ず遺伝し、他の変異に屈することはない",
        "variation_range": (1.0, 1.0),
    },
    # --- 新特性: 禁忌・背反・禁断 ---
    "anti_taboo": {
        "desc": "対禁忌: 禁忌を討つ者。禁忌深度を持つ相手に対して戦闘能力が向上する",
    },
    "antinomy": {
        "desc": "背反: 世界の理への反逆者。初期能力と成長速度が低下するが、禁忌の呪いを克服する",
        "hp_mod": 0.8,
        "atk_mod": 0.8,
        "def_mod": 0.8,
        "growth_mod": 0.7,
    },
    "the_forbidden": {
        "desc": "禁断: かつて、それが生まれるまでは、禁忌は禁忌ではなかった。",
    },
}

# 突然変異で発生する希少遺伝子のスロットと出現候補
MUTATION_GENE_POOL: Dict[str, List[str]] = {
    "growth": ["unlimited", "parasitic"],
    "vitality": ["undead", "chimera", "blue_blood"],
    "potential": ["supernova", "singularity", "anti_taboo"],
    "body": ["gold_horn", "red_back", "odd_eye", "crystalized", "glass_blade"],
}


class GeneticConstants:
    """遺伝システムで使用する定数と定義。"""

    TRAIT_GENES = TRAIT_GENES
    TRAIT_EFFECTS = TRAIT_EFFECTS
    MUTATION_GENE_POOL = MUTATION_GENE_POOL
