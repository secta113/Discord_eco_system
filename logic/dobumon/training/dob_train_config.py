from typing import Dict, Tuple

# 練習メニュー定義
# Weight: 相対的な上昇比率 (負の値は減少)
# Fatigue: HP減少割合 (0.01 = 1%)
TRAINING_MENUS = {
    "strength": {
        "name": "筋トレ",
        "weights": {"atk": 4, "defense": 2, "spd": -1},
        "fatigue": 0.05,
    },
    "running": {
        "name": "走り込み",
        "weights": {"eva": 4, "spd": 2},
        "fatigue": 0.05,
    },
    "ukemi": {
        "name": "受け身",
        "weights": {"defense": 4, "hp": 2, "eva": -1},
        "fatigue": 0.03,
    },
    "shadow": {
        "name": "シャドーボクシング",
        "weights": {"atk": 2, "spd": 2, "eva": 1},
        "fatigue": 0.15,
    },
    "sparring": {
        "name": "スパーリング",
        "weights": {"atk": 1.5, "defense": 1.5, "spd": 1.5},
        "fatigue": 0.10,
    },
    "massage": {
        "name": "マッサージ・お昼寝",
        "weights": {},
        "fatigue": -1.0,  # 回復
        "safe": True,  # 寿命リスクなし
    },
}

# ステータス換算用定数
SCALE_FACTORS = {
    "hp": 10.0,
    "atk": 5.0,
    "defense": 4.0,
    "eva": 1.0,
    "spd": 2.0,
}

# 成長・老化係数
LIFESPAN_REDUCTION_RATE_TRAINING = 0.99  # トレーニング1回あたりの寿命残存率 (1%減少)
