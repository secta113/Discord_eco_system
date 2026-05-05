"""
このモジュールは旧リファクタリングの名残です。
現在は logic.dobumon.genetics.traits パッケージが特性ロジックの本体です。
互換性のために TraitRegistry および各特性クラスをエクスポートしています。
"""

from logic.dobumon.genetics.traits.registry import TraitRegistry
from logic.dobumon.genetics.traits.base import BaseMutationTrait as BaseTrait
from logic.dobumon.genetics.traits.standard import (
    EarlyTrait, LateTrait, HardyTrait, FrailTrait, 
    StableTrait, BurstTrait, AestheticTrait
)
from logic.dobumon.genetics.traits.vitality import (
    UndeadTrait, CrystalizedTrait, ChimeraTrait
)
from logic.dobumon.genetics.traits.growth import (
    UnlimitedTrait, ParasiticTrait
)
from logic.dobumon.genetics.traits.potential import (
    SupernovaTrait, SingularityTrait, AntiTabooTrait
)
from logic.dobumon.genetics.traits.body import (
    GoldHornTrait, RedBackTrait, OddEyeTrait, BlueBloodTrait, GlassBladeTrait
)
from logic.dobumon.genetics.traits.taboo import (
    ForbiddenRedTrait, ForbiddenBlueTrait, AntinomyTrait, 
    TheForbiddenTrait
)
