from typing import Dict, Type
from .base import BaseMutationTrait
from .standard import (
    EarlyTrait, LateTrait, HardyTrait, FrailTrait, 
    StableTrait, BurstTrait, AestheticTrait
)
from .vitality import (
    UndeadTrait, CrystalizedTrait, ChimeraTrait
)
from .potential import (
    SupernovaTrait, SingularityTrait, AntiTabooTrait
)
from .growth import (
    UnlimitedTrait, ParasiticTrait
)
from .body import (
    GoldHornTrait, RedBackTrait, OddEyeTrait, BlueBloodTrait, GlassBladeTrait
)
from .taboo import (
    ForbiddenRedTrait, ForbiddenBlueTrait, AntinomyTrait, 
    TheForbiddenTrait
)


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
