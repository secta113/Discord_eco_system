from typing import Any, Dict, List

# --- Genetic Data ---

# 遺伝子の属性定義 [優性アレル: 表現型, 劣性アレル: 表現型]。
TRAIT_GENES: Dict[str, Dict[str, str]] = {
    "growth": {"D": "early", "r": "late", "desc": "成長曲線判定用 locus"},
    "vitality": {"D": "hardy", "r": "frail", "desc": "健康状態判定用 locus"},
    "potential": {"D": "stable", "r": "burst", "desc": "潜在能力の爆発力判定用 locus"},
    "body": {"D": "normal", "r": "aesthetic", "desc": "肉体特徴判定用 locus"},
}

# 突然変異で発生する希少遺伝子のスロットと出現候補
MUTATION_GENE_POOL: Dict[str, List[str]] = {
    "growth": ["unlimited", "parasitic"],
    "vitality": ["undead", "chimera", "crystalized"],
    "potential": ["supernova", "singularity", "anti_taboo", "antinomy"],
    "body": ["gold_horn", "red_back", "odd_eye", "blue_blood", "glass_blade"],
}


class GeneticConstants:
    """遺伝システムで使用する定数と定義。"""

    TRAIT_GENES = TRAIT_GENES
    MUTATION_GENE_POOL = MUTATION_GENE_POOL
