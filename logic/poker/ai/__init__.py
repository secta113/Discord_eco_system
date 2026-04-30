from logic.poker.pk_models import PokerPlayer

from .base_ai import PokerAI
from .brains import CommonAI, LegendaryAI, MonsterAI, RareAI, TrashAI


def get_ai_instance(player: PokerPlayer) -> PokerAI:
    """
    【AIファクトリーメソッド】
    プレイヤーのAIランク付け (player.ai_rank) から、対応するAIアルゴリズムのインスタンスを生成して返します。
    """
    rank_map = {
        "monster": MonsterAI,
        "legendary": LegendaryAI,
        "rare": RareAI,
        "common": CommonAI,
        "trash": TrashAI,
    }
    ai_class = rank_map.get(player.ai_rank, RareAI)
    return ai_class(player)
