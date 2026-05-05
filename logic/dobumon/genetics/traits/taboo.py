from typing import Any

from .base import BaseMutationTrait


class BaseForbiddenTrait(BaseMutationTrait):
    """赤と青の禁忌に共通する振る舞い（寿命の指数減衰、延命不可など）をまとめた基底クラス"""

    def get_initial_lifespan_multiplier(self, dobumon: Any) -> float:
        # 背反・禁断を持つ場合は寿命減衰を無効化（1.0倍）
        traits = getattr(dobumon, "traits", [])
        if "antinomy" in traits or "the_forbidden" in traits:
            return 1.0

        # それ以外は禁忌深度に応じた指数減衰（最低でも1乗分は適用）
        depth = dobumon.genetics.get("forbidden_depth", 0)
        return self.lifespan_mod ** max(1, depth)

    def apply_initial_status(self, dobumon: Any):
        # 1. 共通のステータス補正を適用 (ここで寿命の指数減衰も自動的に適用される)
        super().apply_initial_status(dobumon)

        # 2. 延命不可フラグ
        dobumon.can_extend_lifespan = False

    def can_extend_lifespan(self) -> bool:
        return False


class ForbiddenRedTrait(BaseForbiddenTrait):
    key = "forbidden_red"
    desc = "赤の禁忌: オスの血が濃すぎることによる暴走。圧倒的攻撃力を持つが、不妊となり短命化する"
    atk_mod = 1.5
    spd_mod = 1.2
    lifespan_mod = 0.6

    def apply_initial_status(self, dobumon: Any):
        super().apply_initial_status(dobumon)
        dobumon.is_sterile = True
        # 病気率の極端な上昇 (+0.15)
        # 乗算補正（Hardy等）の後に加算されることで、最低限のペナルティを保証する
        dobumon.illness_rate += 0.15

    def is_sterile(self) -> bool:
        return True


class ForbiddenBlueTrait(BaseForbiddenTrait):
    key = "forbidden_blue"
    desc = (
        "青の禁忌: メスの血が薄すぎることによる神秘。感性が鋭く、生命力が高いが、極めて短命となる"
    )
    hp_mod = 1.2
    eva_mod = 1.2
    lifespan_mod = 0.5

    def apply_initial_status(self, dobumon: Any):
        super().apply_initial_status(dobumon)
        # 病気率の上昇 (+0.10)
        dobumon.illness_rate += 0.10

    def get_consumption_multiplier(self) -> float:
        return 2.0


class AntinomyTrait(BaseMutationTrait):
    key = "antinomy"
    desc = "背反: 世界の理への反逆者。初期能力と成長速度が低下するが、禁忌の呪いを克服する"
    hp_mod = 0.8
    atk_mod = 0.8
    def_mod = 0.8
    growth_mod = 0.7

    def apply_initial_status(self, dobumon: Any):
        super().apply_initial_status(dobumon)
        # 背反は禁忌の呪い（不妊、延命不可）を解除する
        dobumon.is_sterile = False
        dobumon.can_extend_lifespan = True

    def is_sterile(self) -> bool:
        return False


class TheForbiddenTrait(BaseMutationTrait):
    key = "the_forbidden"
    desc = "禁断: かつて、それが生まれるまでは、禁忌は禁忌ではなかった。"

    def apply_initial_status(self, dobumon: Any):
        super().apply_initial_status(dobumon)
        depth = dobumon.genetics.get("forbidden_depth", 0)
        # 禁断個体のバイタル（寿命）は 発生した寿命 × 禁忌深度 となる
        dobumon.lifespan = float(max(1, int(dobumon.lifespan * max(1, depth))))
        dobumon.max_lifespan = dobumon.lifespan

        dobumon.is_sterile = True
        dobumon.can_extend_lifespan = False

    def is_sterile(self) -> bool:
        return True

    def can_extend_lifespan(self) -> bool:
        return False

    def on_growth_multiplier(self, dobumon: Any, current_multiplier: float) -> float:
        depth = dobumon.genetics.get("forbidden_depth", 0)
        # 禁断: 深度 * ボーナス
        return current_multiplier * (max(1, depth) / 0.7)
