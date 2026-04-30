import random
from typing import Tuple

from .evaluator import calculate_economy_weight


def _apply_aggressive(
    base_action: str, base_amount: int, session, ai_player, weight: float, raise_multiplier: float
) -> Tuple[str, int]:
    is_monster = getattr(ai_player, "ai_rank", "") == "monster"
    if base_action in ("call", "check"):
        # Monsterはレイズ転換率を強化
        chance = (0.15 + (weight * 0.1)) * raise_multiplier
        if is_monster:
            chance = min(0.9, chance * 2.0)

        if random.random() < chance:
            # Monsterはレイズ額が通常(2-4倍)より圧倒的に高い(5-10倍)
            low, high = (2, 4) if not is_monster else (5, 10)
            target_amount = session.current_max_bet + session.big_blind * random.randint(low, high)
            if target_amount - ai_player.current_bet >= ai_player.stack:
                return "all_in", 0
            return "raise", target_amount
    return base_action, base_amount


def _apply_timid(
    base_action: str, base_amount: int, session, weight: float, fold_multiplier: float
) -> Tuple[str, int]:
    if weight <= 0:
        return base_action, base_amount

    if weight > 0.05:
        # プリフロップなら強引なフォールドを少し抑える
        is_preflop = len(session.community_cards) == 0
        effective_fold_mul = fold_multiplier * 0.5 if is_preflop else fold_multiplier
        fold_chance = min(0.9, weight * 3.0 * effective_fold_mul)
        if random.random() < fold_chance:
            return "fold", 0
    return base_action, base_amount


def _apply_calculated(
    base_action: str, base_amount: int, session, ai_player, weight: float, fold_multiplier: float
) -> Tuple[str, int]:
    is_monster = getattr(ai_player, "ai_rank", "") == "monster"

    if is_monster:
        # Calculated Monster: 「潜伏する死神」
        # 序盤はあえて弱気に見せてプレイヤーを釣り、終盤に致命的な一撃を与える
        if session.phase in ("pre_flop", "flop"):
            if base_action == "raise":
                return "call", 0  # 強い手でもあえてコールに留める
            return base_action, base_amount
        else:
            # ターン・リバーでは豹変してレイズを仕掛ける
            if base_action in ("call", "check") and random.random() < 0.6:
                target_amount = session.current_max_bet + session.big_blind * random.randint(4, 8)
                return "raise", target_amount
            return base_action, base_amount

    if weight <= 0:
        return base_action, base_amount

    if weight > 0.5:
        is_preflop = len(session.community_cards) == 0
        if is_preflop:
            # プリフロップならパニックフォールドを大幅に抑制
            if random.random() < 0.05 * fold_multiplier:
                return "fold", 0
        elif random.random() < 0.3 * fold_multiplier:
            return "fold", 0
    return base_action, base_amount


def _apply_bluffer(
    base_action: str,
    base_amount: int,
    session,
    weight: float,
    fold_multiplier: float,
    raise_multiplier: float,
) -> Tuple[str, int]:
    if base_action in ("call", "check") and random.random() < 0.25 * raise_multiplier:
        target_amount = session.current_max_bet + session.big_blind * random.randint(1, 3)
        return "raise", target_amount
    if weight > 0.3:
        is_preflop = len(session.community_cards) == 0
        fold_chance = 0.02 if is_preflop else 0.1
        if random.random() < fold_chance * fold_multiplier:
            return "fold", 0
    return base_action, base_amount


def _apply_station(needed: int, weight: float, fold_multiplier: float) -> Tuple[str, int]:
    if needed <= 0:
        return "check", 0
    # コーリング・ステーションは滅多に降りないが、
    # 平均スタックを大きく超える（weight > 1.0）ような無謀な勝負には稀に降りる判定を入れる
    fold_chance = 0.05
    if weight > 1.0:
        # かなり緩やかに上昇させる (weight=2.5で0.08程度)
        fold_chance = min(0.2, fold_chance + (weight - 1.0) * 0.02)

    if random.random() < fold_chance * fold_multiplier:
        return "fold", 0
    return "call", 0


def _apply_shark(
    base_action: str, base_amount: int, session, weight: float, fold_multiplier: float
) -> Tuple[str, int]:
    if base_action == "raise":
        return "raise", base_amount + session.big_blind * 2
    if weight > 0.1:
        is_preflop = len(session.community_cards) == 0
        fold_chance = 0.05 if is_preflop else 0.4
        if random.random() < fold_chance * fold_multiplier:
            return "fold", 0
    return base_action, base_amount


def _apply_normal(
    base_action: str, base_amount: int, session, weight: float, fold_multiplier: float
) -> Tuple[str, int]:
    if weight > 0.2:
        is_preflop = len(session.community_cards) == 0
        base_fold = 0.05 if is_preflop else 0.2
        if random.random() < (base_fold + (weight * 0.5)) * fold_multiplier:
            return "fold", 0
    return base_action, base_amount


def apply_personality(base_action: str, base_amount: int, session, ai_player) -> Tuple[str, int]:
    """
    【AI性格（Personality）適用モジュール】
    """
    if base_action == "fold" or base_action == "all_in":
        return base_action, base_amount

    # 重みは「現状の維持コスト」だけで計算する。
    # AIが自発的に検討しているレイズ額は、フォールド判定の「恐怖心」には含めない。
    needed = session.current_max_bet - ai_player.current_bet
    weight = calculate_economy_weight(session, needed)

    personality = ai_player.personality or "normal"
    risk_level = getattr(ai_player, "risk_level", 0.5)

    fold_multiplier = max(0.2, 1.5 - risk_level)
    raise_multiplier = 0.5 + risk_level

    # ----------------------------------------------------
    # 理性の獲得: 高ランクAIは性格(ブラフや恐怖)の暴走を抑え込む
    # ----------------------------------------------------
    ai_rank = getattr(ai_player, "ai_rank", "")
    is_high_tier = ai_rank in ("legendary", "monster")
    if is_high_tier:
        fold_multiplier *= 0.3
        raise_multiplier *= 0.3

    if personality == "aggressive":
        res_action, res_amt = _apply_aggressive(
            base_action, base_amount, session, ai_player, weight, raise_multiplier
        )
    elif personality == "timid":
        res_action, res_amt = _apply_timid(
            base_action, base_amount, session, weight, fold_multiplier
        )
    elif personality == "calculated":
        res_action, res_amt = _apply_calculated(
            base_action, base_amount, session, ai_player, weight, fold_multiplier
        )
    elif personality == "bluffer":
        res_action, res_amt = _apply_bluffer(
            base_action, base_amount, session, weight, fold_multiplier, raise_multiplier
        )
    elif personality == "station":
        res_action, res_amt = _apply_station(needed, weight, fold_multiplier)
    elif personality == "shark":
        res_action, res_amt = _apply_shark(
            base_action, base_amount, session, weight, fold_multiplier
        )
    else:
        # default / normal
        res_action, res_amt = _apply_normal(
            base_action, base_amount, session, weight, fold_multiplier
        )

    # ----------------------------------------------------
    # 強い意志の保護:
    # 本体がRaise(勝算あり)と判断したのに恐怖でFoldした場合、手放さずにCallで留める
    # ----------------------------------------------------
    if base_action == "raise" and res_action == "fold":
        return "call", 0

    return res_action, res_amt
