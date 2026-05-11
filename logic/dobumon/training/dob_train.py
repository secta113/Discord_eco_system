import random
from typing import Dict

from core.utils.time_utils import get_jst_today
from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.dob_shop.dob_shop_effect_manager import DobumonShopEffectManager
from logic.dobumon.genetics.traits.registry import TraitRegistry

from .dob_train_config import (
    LIFESPAN_REDUCTION_RATE_TRAINING,
    SCALE_FACTORS,
    TRAINING_MENUS,
)


class TrainingEngine:
    """
    怒武者のトレーニングにおける成長計算を司るエンジン。
    """

    TRAINING_MENUS = TRAINING_MENUS

    @staticmethod
    def calculate_training_cost(dobu: Dobumon) -> int:
        """
        育成費用を計算します。
        回数に応じて上昇し、懐き度により割引されます。
        """
        today_str = get_jst_today()
        # 日付が今日でない場合は回数 0 として扱う
        count = dobu.today_train_count if dobu.last_train_date == today_str else 0

        if count == 0:
            base_cost = 500
        elif count == 1:
            base_cost = 1000
        elif count == 2:
            base_cost = 2000
        else:
            base_cost = 4000

        discount_rate = dobu.affection_training_discount
        return int(base_cost * (1 - discount_rate))

    @staticmethod
    def calculate_menu_gains(dobu: Dobumon, menu_key: str) -> Dict:
        """
        指定されたメニューによる全ステータスの上昇量を計算します。
        """
        menu = TrainingEngine.TRAINING_MENUS.get(menu_key)
        if not menu:
            return {"success": False, "msg": "無効なメニューです。"}

        weights = menu["weights"]
        # 重みの絶対値の合計で正規化
        total_weight = sum(abs(w) for w in weights.values()) or 1.0

        # ベースとなる成長1回分の「力」
        base_power = 1.0

        # 大成功判定 (懐き度による確率変動)
        # ベース10% + 懐き度ボーナス (最大適用時のキャップ等は維持)
        chance = 0.1 + dobu.affection_great_success_bonus

        # 特性による補正
        max_chance = 0.5
        for t in dobu.traits:
            trait_obj = TraitRegistry.get(t)
            chance *= trait_obj.great_success_mod
            if t == "burst":
                max_chance = 0.7  # 爆発時はキャップを引き上げ

        great_success_chance = min(max_chance, chance)
        is_great = random.random() < great_success_chance
        great_multiplier = 1.5 if is_great else 1.0

        gains = {}
        # ステータス換算用定数
        scale_factors = SCALE_FACTORS

        for stat, w in weights.items():
            # 1. 個体値 (IV)
            iv_val = dobu.iv.get(stat, 1.0)

            # 2. 収穫逓減 (成長鈍化)と特性の影響
            current_val = getattr(dobu, stat, 0.0)
            growth_multiplier = TrainingEngine._get_growth_multiplier(current_val)
            for t in dobu.traits:
                growth_multiplier = TraitRegistry.get(t).on_growth_multiplier(
                    dobu, growth_multiplier
                )

            # 3. 乱数 (80% ~ 120%)
            variance = random.uniform(0.8, 1.2)

            # 4. 単位計算
            # (重み / 合計重み) * セッション定数
            unit_gain = (w / total_weight) * base_power

            # 5. SPDに対する一律 0.5倍 補正
            spd_multiplier = 0.5 if stat == "spd" else 1.0

            # 最終計算
            # ショップアイテム効果の集計 (EffectManagerを利用)
            modifiers = DobumonShopEffectManager.get_training_modifiers(dobu)
            shop_multiplier = modifiers["multiplier"]

            # 冷却シップ: 収穫逓減を無視
            if modifiers["ignore_diminishing_returns"]:
                growth_multiplier = 1.0

            gain = (
                unit_gain
                * scale_factors.get(stat, 1.0)
                * iv_val
                * growth_multiplier
                * variance
                * great_multiplier
                * spd_multiplier
                * dobu.growth_multiplier  # ライフステージによる追加倍率
                * shop_multiplier
            )

            # 最小単位 0.01 (減少の場合は制限なし)
            if w > 0:
                gain = max(0.01, gain)

            gains[stat] = round(gain, 2)

        return {
            "success": True,
            "gains": gains,
            "is_great": is_great,
            "fatigue": menu["fatigue"],
            "safe": menu.get("safe", False),
        }

    @staticmethod
    def _get_growth_multiplier(stat_value: float) -> float:
        """
        ステータス値に応じた成長減衰率を返します（滑らかな減衰曲線）。
        1.0 / (1.0 + (value/500)^2) をベースに調整。
        """
        # 500で効率50%程度になる曲線
        eff = 1.0 / (1.0 + pow(stat_value / 500, 2))
        # 最低保証 20%
        return max(0.2, eff)

    @staticmethod
    def apply_training_results(dobu: Dobumon, result: Dict) -> Dict:
        """
        トレーニング計算結果を実際に Dobumon オブジェクトに適用します。
        """
        gains = result["gains"]
        fatigue_rate = result["fatigue"]
        is_safe = result["safe"]

        # 1. ステータスの更新
        for stat, gain in gains.items():
            current_val = getattr(dobu, stat)
            setattr(dobu, stat, max(1.0, current_val + gain))

        # 2. 懐き度の向上
        DAILY_AFFECTION_LIMIT = 8
        today_str = get_jst_today()
        # 日付が今日であり、かつ回数が 5 以上の場合にオーバーワークとする
        overworked = dobu.last_train_date == today_str and dobu.today_train_count >= 5

        # オーバーワーク時は上昇しない
        if not overworked and dobu.today_affection_gain < DAILY_AFFECTION_LIMIT:
            # 上昇量の決定
            if is_safe:  # マッサージ・お昼寝
                # なつき度の上昇は1日1回目のみ
                gain = 2 if dobu.today_massage_count == 0 else 0
            elif result.get("is_great"):  # 大成功
                gain = 2
            else:  # 通常トレーニング
                gain = 1

            # 上限を超えないように適用
            actual_gain = min(gain, DAILY_AFFECTION_LIMIT - dobu.today_affection_gain)
            dobu.affection += actual_gain
            dobu.today_affection_gain += actual_gain

        # 3. 疲労（HP減少・回復）の適用
        current_hp_val = dobu.health if dobu.health > 0 else dobu.hp
        if fatigue_rate > 0:
            loss = dobu.hp * fatigue_rate
            dobu.health = max(1.0, current_hp_val - loss)
        elif fatigue_rate < 0:
            recovery = dobu.hp * abs(fatigue_rate)
            dobu.health = min(dobu.hp, current_hp_val + recovery)

        # 4. 寿命減少リスク
        lifespan_lost = False
        is_alive_result = dobu.is_alive
        if not is_safe:
            if overworked:
                # 6回目以降: 15% + (count-6)*5% + illness_rate
                base_prob = 0.15 + (max(0, dobu.today_train_count - 5) * 0.05)
                risk_prob = base_prob + dobu.illness_rate

                # 寿命消費倍率 (モデルで一括計算)
                consumption_mod = dobu.consumption_mod

                if random.random() < (risk_prob * consumption_mod):
                    dobu.lifespan *= LIFESPAN_REDUCTION_RATE_TRAINING
                    lifespan_lost = True
                    if dobu.lifespan < 1.0:
                        is_alive_result = False
            else:
                # 1〜5回目: 安全圏 (消費 0)
                pass

        if not is_safe:
            dobu.today_train_count += 1

            # 5. ショップアイテム効果の消費
            # 劇薬とシップは1回使い切り
            flags_to_remove = ["suicidal_drug", "cooling_sheet"]
            for f in flags_to_remove:
                if f in dobu.shop_flags:
                    del dobu.shop_flags[f]

            # ブースターは5回分
            if "muscle_booster" in dobu.shop_flags:
                dobu.shop_flags["muscle_booster"]["remaining"] -= 1
                if dobu.shop_flags["muscle_booster"]["remaining"] <= 0:
                    del dobu.shop_flags["muscle_booster"]

        # 戻り値に状態変化を含める
        update_info = {
            "overworked": overworked,
            "lifespan_lost": lifespan_lost,
            "fatigue_rate": fatigue_rate,
            "is_alive": is_alive_result,
        }
        return update_info
