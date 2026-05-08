from typing import Dict, Optional

from logic.dobumon.core.dob_logger import DobumonLogger
from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.genetics.traits.registry import TraitRegistry
from logic.dobumon.training import WildGrowthEngine


class BattleSettlementManager:
    """
    怒武者の戦闘終了後の決済（報酬計算、健康状態、勝利数、死亡処理）を管理するクラス。
    """

    # 報酬定数
    WILD_BATTLE_REWARD = 10000
    CHALLENGE_BASE_REWARD = 30000
    CHALLENGE_WIN_COUNT_BONUS = 10000

    @staticmethod
    def settle_pvp(winner: Dobumon, loser: Dobumon, battle_result: Optional[Dict] = None) -> Dict:
        """
        PvP（決闘）の結果をシステムに反映させます。
        """
        # 1. 報酬計算
        reward = BattleSettlementManager.CHALLENGE_BASE_REWARD + (
            loser.win_count * BattleSettlementManager.CHALLENGE_WIN_COUNT_BONUS
        )

        exp_multiplier = 1.0
        for t in winner.traits:
            exp_multiplier, reward = TraitRegistry.get(t).on_combat_reward(exp_multiplier, reward)
        reward = int(reward)

        # 2. 敗北者の処理
        # [REFACTORED] Manager.handle_death 経由で処理するため、ここでの die() は削除
        loser.health = loser.hp  # [DEBUG] 敗北後も即座に再戦可能な暫定仕様

        # 3. 勝利者の更新
        if battle_result:
            # winner は常に戦闘時の残存HPに更新
            if winner.dobumon_id == battle_result.get("winner_id"):
                winner.health = (
                    battle_result.get("p1_remaining_hp")
                    if winner.dobumon_id == battle_result.get("p1_id")
                    else battle_result.get("p2_remaining_hp")
                )
            else:
                # 万が一 winner_id が不一致な場合のフォールバック（通常は起きない）
                pass

        winner.win_count += 1

        DobumonLogger.battle(
            "Settled PvP", f"Winner={winner.name} vs Loser={loser.name} | Reward={reward}"
        )

        return {
            "success": True,
            "reward": reward,
            "winner_owner_id": winner.owner_id,
            "loser_owner_id": loser.owner_id,
            "winner_name": winner.name,
            "loser_name": loser.name,
        }

    @staticmethod
    def settle_wild(
        player_dobu: Dobumon,
        wild_dobu_name: str,
        winner_id: str,
        battle_result: Optional[Dict] = None,
    ) -> Dict:
        """
        野生戦の結果をシステムに反映させます。
        """
        if winner_id == player_dobu.dobumon_id:
            # プレイヤー勝利
            if battle_result:
                player_dobu.health = battle_result.get("p1_remaining_hp")
            player_dobu.win_count += 1
            reward = BattleSettlementManager.WILD_BATTLE_REWARD

            exp_multiplier = 1.0
            for t in player_dobu.traits:
                exp_multiplier, reward = TraitRegistry.get(t).on_combat_reward(
                    exp_multiplier, reward
                )
            reward = int(reward)

            # 成長（経験値獲得）の計算
            gains = WildGrowthEngine.calculate_gains(player_dobu, exp_multiplier=exp_multiplier)

            return {
                "success": True,
                "winner": "player",
                "reward": reward,
                "player_owner_id": player_dobu.owner_id,
                "gains": gains,
            }
        else:
            # プレイヤー敗北
            # [REFACTORED] Manager.handle_death 経由で処理するため、ここでの die() は削除
            player_dobu.health = player_dobu.hp  # [DEBUG]

            DobumonLogger.battle(
                "Settled Wild (LOSS)", f"Player={player_dobu.name} vs Wild({wild_dobu_name})"
            )
            return {
                "success": True,
                "winner": "wild",
                "reward": 0,
                "player_owner_id": player_dobu.owner_id,
            }
