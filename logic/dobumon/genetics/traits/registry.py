from typing import Dict, Type

from .base import BaseMutationTrait
from .body import BlueBloodTrait, GlassBladeTrait, GoldHornTrait, OddEyeTrait, RedBackTrait
from .growth import ParasiticTrait, UnlimitedTrait
from .potential import AntiTabooTrait, SingularityTrait, SupernovaTrait
from .standard import (
    AestheticTrait,
    BurstTrait,
    EarlyTrait,
    FrailTrait,
    HardyTrait,
    LateTrait,
    StableTrait,
)
from .taboo import AntinomyTrait, ForbiddenBlueTrait, ForbiddenRedTrait, TheForbiddenTrait
from .vitality import ChimeraTrait, CrystalizedTrait, UndeadTrait


class TraitRegistry:
    """全ての特性クラスを管理するレジストリ。"""

    _classes: Dict[str, Type[BaseMutationTrait]] = {
        # Standard
        "early": EarlyTrait,
        "late": LateTrait,
        "hardy": HardyTrait,
        "frail": FrailTrait,
        "stable": StableTrait,
        "burst": BurstTrait,
        "aesthetic": AestheticTrait,
        # Growth
        "unlimited": UnlimitedTrait,
        "parasitic": ParasiticTrait,
        # Vitality
        "undead": UndeadTrait,
        "crystalized": CrystalizedTrait,
        "chimera": ChimeraTrait,
        # Potential
        "supernova": SupernovaTrait,
        "singularity": SingularityTrait,
        # Body
        "gold_horn": GoldHornTrait,
        "red_back": RedBackTrait,
        "odd_eye": OddEyeTrait,
        "blue_blood": BlueBloodTrait,
        "glass_blade": GlassBladeTrait,
        # Taboo
        "forbidden_red": ForbiddenRedTrait,
        "forbidden_blue": ForbiddenBlueTrait,
        "antinomy": AntinomyTrait,
        "the_forbidden": TheForbiddenTrait,
        "anti_taboo": AntiTabooTrait,
    }

    @classmethod
    def get(cls, key: str) -> BaseMutationTrait:
        """キーに対応する特性クラスのインスタンスを返します。"""
        trait_class = cls._classes.get(key, BaseMutationTrait)
        return trait_class()

    @classmethod
    def get_all_keys(cls) -> list[str]:
        return list(cls._classes.keys())
