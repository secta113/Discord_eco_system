from enum import Enum


class JPRarity(Enum):
    """ジャックポットのレアリティ定義 (v2.11)"""

    NONE = 0
    COMMON = 1  # 3%
    RARE = 2  # 10%
    EPIC = 3  # 30%
    LEGENDARY = 4  # 100%


class GameType(Enum):
    """ゲーム種別定義"""

    POKER = "Poker"
    BLACKJACK = "Blackjack"
    CHINCHIRO = "Chinchiro"
