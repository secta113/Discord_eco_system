"""
このモジュールは旧リファクタリングの名残です。
現在は logic.dobumon.genetics.traits パッケージが特性ロジックの本体です。
互換性のために TraitRegistry および各特性クラスをエクスポートしています。
"""

from logic.dobumon.genetics.traits.base import BaseMutationTrait as BaseTrait
from logic.dobumon.genetics.traits.body import (
    BlueBloodTrait,
    GlassBladeTrait,
    GoldHornTrait,
    OddEyeTrait,
    RedBackTrait,
)
from logic.dobumon.genetics.traits.growth import ParasiticTrait, UnlimitedTrait
from logic.dobumon.genetics.traits.potential import AntiTabooTrait, SingularityTrait, SupernovaTrait
from logic.dobumon.genetics.traits.registry import TraitRegistry
from logic.dobumon.genetics.traits.standard import (
    AestheticTrait,
    BurstTrait,
    EarlyTrait,
    FrailTrait,
    HardyTrait,
    LateTrait,
    StableTrait,
)
from logic.dobumon.genetics.traits.taboo import (
    AntinomyTrait,
    ForbiddenBlueTrait,
    ForbiddenRedTrait,
    TheForbiddenTrait,
)
from logic.dobumon.genetics.traits.vitality import ChimeraTrait, CrystalizedTrait, UndeadTrait
