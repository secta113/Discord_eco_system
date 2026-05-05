from typing import Any, Dict, Optional, Tuple


class BaseMutationTrait:
    """
    全ての突然変異・特性・禁忌の基底クラス。
    各特性はこのクラスを継承し、必要に応じてプロパティやメソッドをオーバーライドします。
    """

    key: str = ""
    desc: str = ""

    # ステータス補正倍率
    hp_mod: float = 1.0
    atk_mod: float = 1.0
    def_mod: float = 1.0
    eva_mod: float = 1.0
    spd_mod: float = 1.0
    illness_mod: float = 1.0
    lifespan_mod: float = 1.0
    growth_mod: float = 1.0
    reward_mod: float = 1.0
    mutation_mod: float = 1.0
    great_success_mod: float = 1.0

    # 交配時の個体値振れ幅補正
    variation_range: Optional[Tuple[float, float]] = None

    def apply_initial_status(self, dobumon: Any):
        """
        個体生成時に初期ステータスや寿命に補正を適用します。
        """
        dobumon.hp = max(1, int(dobumon.hp * self.hp_mod))
        dobumon.atk = max(1, int(dobumon.atk * self.atk_mod))
        dobumon.defense = max(1, int(dobumon.defense * self.def_mod))
        dobumon.eva = max(1, int(dobumon.eva * self.eva_mod))
        dobumon.spd = max(1, int(dobumon.spd * self.spd_mod))

        # 寿命補正
        dobumon.lifespan = float(max(1, int(dobumon.lifespan * self.lifespan_mod)))
        dobumon.max_lifespan = dobumon.lifespan

        # 病気率補正
        dobumon.illness_rate *= self.illness_mod

        # 特殊フラグ
        if self.is_sterile():
            dobumon.is_sterile = True
        if not self.can_extend_lifespan():
            dobumon.can_extend_lifespan = False

    def get_stat_multiplier(self, stat_name: str) -> float:
        """特定のステータス倍率を返します（互換性用）"""
        if stat_name == "illness":
            return self.illness_mod
        if stat_name == "def":
            return self.def_mod
        return getattr(self, f"{stat_name}_mod", 1.0)

    def get_consumption_multiplier(self) -> float:
        """老化速度（consumption_mod）に対する倍率を返します。"""
        return 1.0

    def modifies_battle_death(self) -> bool:
        """戦闘での死亡（ロスト）を無効化するかどうか。"""
        return False

    def is_sterile(self) -> bool:
        """不妊状態（交配不可）にするかどうか。"""
        return False

    def can_extend_lifespan(self) -> bool:
        """延命アイテムの使用を許可するかどうか。"""
        return True

    def on_growth_multiplier(self, dobumon: Any, current_multiplier: float) -> float:
        """トレーニング成長倍率に介入します。"""
        return current_multiplier * self.growth_mod

    def on_combat_start(self, dobumon: Any, opponent: Any) -> Dict[str, float]:
        """戦闘開始時のステータス補正を返します。"""
        return {}

    def on_inherit_allele(self) -> str:
        """次世代への遺伝時にアレルを書き換える場合に使用します。"""
        return self.key

    def on_combat_reward(self, exp_gain: float, pt_reward: int) -> Tuple[float, int]:
        """戦闘報酬（経験値、ポイント）を補正します。"""
        return exp_gain * self.reward_mod, int(pt_reward * self.reward_mod)
