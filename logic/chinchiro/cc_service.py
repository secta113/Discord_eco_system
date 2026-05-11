from typing import Dict, List

from core.economy import wallet
from logic.bet_service import BetService
from logic.constants import GameType, JPRarity
from managers.game_session import BaseGameSession

from .cc_exceptions import ChinchiroTurnError
from .cc_hospitality import ChinchiroHospitality
from .cc_models import ChinchiroHand, ChinchiroPlayer
from .cc_rules import ChinchiroRules


class ChinchiroService(BaseGameSession):
    """
    チンチロリンのゲーム進行管理。
    cc_models, cc_rules, cc_hospitality に処理を委譲。
    """

    DICE_EMOJI = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}

    def __init__(self, channel_id, bet_amount):
        super().__init__(channel_id, bet_amount)
        self.player_states: Dict[int, ChinchiroPlayer] = {}
        self.current_roll_count = 0

    @property
    def game_type(self) -> str:
        return "chinchiro"

    @property
    def game_name(self) -> str:
        return "チンチロリン"

    @property
    def min_players(self) -> int:
        return 2

    def to_dict(self):
        data = super().to_dict()
        data["player_states"] = {str(k): v.to_dict() for k, v in self.player_states.items()}
        data["current_roll_count"] = self.current_roll_count
        return data

    @classmethod
    def from_dict(cls, data):
        obj = super().from_dict(data)
        states = data.get("player_states", {})
        obj.player_states = {int(k): ChinchiroPlayer.from_dict(v) for k, v in states.items()}
        obj.current_roll_count = data.get("current_roll_count", 0)
        return obj

    def roll_action(self, user_id: int):
        """ダイスを振り、必要に応じて接待を適用する。"""
        current_p = self.get_current_player()
        if not current_p or current_p["id"] != user_id:
            raise ChinchiroTurnError(current_p["mention"] if current_p else "不明なプレイヤー")

        self.current_roll_count += 1
        uid = current_p["id"]

        dice = [random_randint(1, 6) for _ in range(3)]

        # 接待ロジック適用
        p_state = self.player_states.get(uid)
        status_rank = p_state.asset_rank if p_state else None
        dice, h_triggered = ChinchiroHospitality.apply_roll_protection(
            uid, self.current_roll_count, dice, status_rank=status_rank
        )

        role_name, strength = ChinchiroRules.calculate_role(dice)
        dice_str = self._format_dice(dice)

        # 確定判定
        is_fixed = True
        if strength == 0 and self.current_roll_count < 3:
            is_fixed = False

        return dice, dice_str, role_name, strength, is_fixed, h_triggered

    def finalize(self):
        """勝敗決定、配当、共通手数料、ジャックポット清算を実行。"""
        if not self.player_states:
            return None, [], 0

        # スコアリスト作成
        scores = []
        user_names = {p["id"]: p["name"] for p in self.players}
        for p_state in self.player_states.values():
            if p_state.hand:
                uid = p_state.user_id
                scores.append(
                    {
                        "id": uid,
                        "name": user_names.get(uid, f"User:{uid}"),
                        "strength": p_state.hand.strength,
                        "text": f"{self._format_dice(p_state.hand.dice)} 【{p_state.hand.role_name}】",
                        "hospitality_triggered": p_state.hand.hospitality_triggered,
                    }
                )

        winner_data = ChinchiroRules.determine_winner(scores)

        # 実入金（人間プレイヤーの賭け金合計）を算出 (将来のNPC対応のため ID > 0 で判定)
        real_pot = sum(self.bet_amount for p in self.players if p["id"] > 0)
        original_pot = self.pot

        # 全員役なし判定
        is_all_no_role = all(s["strength"] <= 0 for s in scores)
        if is_all_no_role:
            BetService.add_to_jackpot_real_only(self.pot, original_pot, real_pot, "Chinchiro")
            for s in scores:
                s["text"] += " ⚠️ **全員役なしのためポットは没収（ジャックポットへ）**"
            self.status = "settled"
            return None, scores, 0

        # 通常配当実行
        is_pvp = len(self.players) >= 2
        is_oya_winner = winner_data["id"] == self.players[0]["id"]

        # 内訳計算 (税引後配当, 徴収税額)
        net_pot, tax = ChinchiroRules.get_settlement_breakdown(self.pot, is_pvp, is_oya_winner)

        actual_payout = BetService.payout(
            winner_data["id"], net_pot, is_pvp=is_pvp, reason="チンチロリン勝利配当"
        )

        # 税金の処理 (Jackpotへ)
        if tax > 0:
            BetService.add_to_jackpot_real_only(tax, original_pot, real_pot, "Chinchiro")
            winner_data["text"] += f"\n💰 **親の責任 (Oya Tax): -{tax}pts 徴収済み**"

        # ジャックポット清算と演出
        for s in scores:
            uid = s["id"]
            h_triggered = s.get("hospitality_triggered", False)

            if h_triggered:
                s["text"] += "\n✨ **幸運の女神が微笑んでいるようです！**"

            # 希少役判定とJP
            jp_payout = 0
            if "ピンゾロ" in s["text"]:
                if h_triggered:
                    s["text"] += "\n⚠️ **女神がボーナスを持ち逃げしました…**"
                else:
                    jp_payout = BetService.execute_jackpot(
                        uid, GameType.CHINCHIRO, JPRarity.RARE, "ピンゾロ"
                    )
            elif "アラシ" in s["text"]:
                if h_triggered:
                    s["text"] += "\n⚠️ **女神がボーナスを持ち逃げしました…**"
                else:
                    jp_payout = BetService.execute_jackpot(
                        uid, GameType.CHINCHIRO, JPRarity.COMMON, "アラシ"
                    )

            if jp_payout > 0:
                s["text"] += f" 🎰 Jackpot +{jp_payout}pts!"

        self.status = "settled"

        # 統計更新
        for s in scores:
            uid = s["id"]
            is_win = uid == winner_data["id"]
            wallet.update_stats(uid, is_win=is_win, amount_won=actual_payout if is_win else 0)

        return winner_data, scores, actual_payout

    def next_turn(self):
        """手番交代時のリセット"""
        self.current_roll_count = 0
        return self.rotate_turn()

    def record_hand(
        self, user_id: int, dice_list: List[int], role_name: str, strength: int, h_triggered: bool
    ):
        """ユーザーの手札を確定記録する"""
        hand = ChinchiroHand(dice_list, self.current_roll_count)
        hand.role_name = role_name
        hand.strength = strength
        hand.is_fixed = True
        hand.hospitality_triggered = h_triggered

        player = self.player_states.get(user_id)
        if not player:
            # 参加者リストからランクを取得（共通化対応）
            asset_rank = "Standard"
            for p in self.players:
                if p["id"] == user_id:
                    asset_rank = p.get("asset_rank", "Standard")
                    break
            player = ChinchiroPlayer(user_id, asset_rank=asset_rank)
            self.player_states[user_id] = player

        player.set_hand(hand)

    def _format_dice(self, dice):
        return " ".join([self.DICE_EMOJI.get(x, "?") for x in dice])


def random_randint(min_val, max_val):
    import random

    return random.randint(min_val, max_val)
