import json
import os
from typing import Dict, List, Optional


class WildBattleConfig:
    _data = None
    _FILE_PATH = "data/dobumon/wild_maps.json"

    @classmethod
    def _load(cls):
        if cls._data is None:
            # プロジェクトルートからの相対パス
            full_path = os.path.join(os.getcwd(), cls._FILE_PATH)
            with open(full_path, "r", encoding="utf-8") as f:
                cls._data = json.load(f)

    @classmethod
    def get_ranks(cls) -> Dict:
        cls._load()
        return cls._data["ranks"]

    @classmethod
    def get_rank(cls, rank_key: str) -> Optional[Dict]:
        return cls.get_ranks().get(rank_key)

    @classmethod
    def get_maps(cls, rank_key: str) -> List[Dict]:
        """指定されたランクで使用可能なマップ一覧を取得します。"""
        cls._load()
        rank_info = cls.get_rank(rank_key)
        if not rank_info or "maps" not in rank_info:
            return []
        return rank_info["maps"]

    @classmethod
    def get_map(cls, rank_key: str, map_id: str) -> Optional[Dict]:
        """指定されたランクの特定のマップ情報を取得します。"""
        for m in cls.get_maps(rank_key):
            if m["id"] == map_id:
                return m
        return None

    @classmethod
    def get_disadvantage_bonus(cls) -> float:
        cls._load()
        return cls._data.get("disadvantage_bonus", 0.5)
