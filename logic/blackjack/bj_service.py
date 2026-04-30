import random
from typing import Dict, List

from core.economy import wallet
from core.utils.constants import GameType, JPRarity
from core.utils.logger import Logger
from logic.bet_service import BetService
from managers.game_session import BaseGameSession

from .bj_deck import Deck
from .bj_exceptions import (
    BlackjackActionError,
    BlackjackError,
    BlackjackInsufficientFundsError,
    BlackjackTurnError,
)
from .bj_hospitality import BlackjackHospitality
from .bj_models import BlackjackHand, BlackjackPlayer
from .bj_rules import BlackjackRules


class BlackjackService(BaseGameSession):
    """
    ブラックジャックのゲームロジック（ソロ・マルチ兼用）。
    BaseGameSessionを継承し、募集・参加・開始のフローを持つ。
    """

    def __init__(self, channel_id, bet_amount):
        super().__init__(channel_id, bet_amount)
        self.deck = Deck()
        self.dealer_hand = []
        # プレイヤーごとのゲーム状態 {user_id: BlackjackPlayer}
        self.player_states: Dict[int, BlackjackPlayer] = {}
        self.is_dealer_turn_executed = False

    @property
    def game_type(self) -> str:
        return "blackjack"

    @property
    def game_name(self) -> str:
        return "ブラックジャック"

    def to_dict(self):
        data = super().to_dict()
        data["deck"] = {"cards": self.deck.cards}
        data["dealer_hand"] = self.dealer_hand
        data["player_states"] = {str(k): v.to_dict() for k, v in self.player_states.items()}
        data["is_dealer_turn_executed"] = self.is_dealer_turn_executed
        return data

    @classmethod
    def from_dict(cls, data):
        obj = super().from_dict(data)

        deck_obj = Deck()
        if "deck" in data and "cards" in data["deck"]:
            deck_obj.cards = data["deck"]["cards"]
        obj.deck = deck_obj

        obj.dealer_hand = data.get("dealer_hand", [])
        states = data.get("player_states", {})
        obj.player_states = {
            int(k): BlackjackPlayer.from_dict(int(k), v) for k, v in states.items()
        }
        obj.is_dealer_turn_executed = data.get("is_dealer_turn_executed", False)
        return obj

    def start_game(self):
        """ゲーム開始時の初期化（カード配布）"""
        self.status = "playing"
        self.is_dealer_turn_executed = False

        # ディーラーの初期配布
        self.dealer_hand = [self.deck.draw(), self.deck.draw()]

        # 参加者全員にカードを配る
        for p in self.players:
            uid = p["id"]
            asset_rank = p.get("asset_rank", "Standard")
            cards = [self.deck.draw(), self.deck.draw()]

            hand = BlackjackHand(cards, self.bet_amount)
            if hand.is_bj:
                hand.status = "blackjack"

            player = BlackjackPlayer(uid, asset_rank=asset_rank)
            player.add_hand(hand)
            self.player_states[uid] = player

        self.advance_turn_if_needed()

    def advance_turn_if_needed(self) -> bool:
        """まだプレイ中のプレイヤーが出るまでターンを進める"""
        while True:
            p = self.get_current_player()
            if not p:
                return False

            player = self.player_states[p["id"]]
            hand = player.get_active_hand()

            if not hand:
                if not self.rotate_turn():
                    return False
                continue

            # 現在の手札が終了している場合、次の手札があるか確認
            if hand.status != "playing":
                if player.active_hand_index < len(player.hands) - 1:
                    player.active_hand_index += 1
                    # 次の手札を確認
                    continue

            # 現在の手札がプレイ中ならそのまま続行
            if hand.status == "playing":
                return True

            # 全ての手札が終わっているなら次のプレイヤーへ
            if not self.rotate_turn():
                return False

    def current_player_action(self, user_id: int, action_type: str):
        """
        現在の手番プレイヤーのアクション処理
        """
        p_obj = self.get_current_player()
        if not p_obj or p_obj["id"] != user_id:
            raise BlackjackTurnError()

        uid = p_obj["id"]
        player = self.player_states[uid]
        hand = player.get_active_hand()

        if action_type == "hit":
            # 接待ロジック: Hit時バースト回避
            BlackjackHospitality.apply_hit_protection(self.deck, uid, hand, player.asset_rank)

            card = self.deck.draw()
            hand.add_card(card)
            score = hand.score
            card_str = Deck.format_card(card)

            # 結果判定 (モデル側で status が更新されている)
            if hand.status == "stand":  # 6-Card Charlie 等
                return (
                    f"引いたカード: {card_str} (計: {score}) -> 🏆 **6-Card Charlie!**",
                    True,
                )
            elif hand.status == "bust":
                return f"引いたカード: {card_str} (計: {score}) -> 💥 バースト！", True
            else:
                return f"引いたカード: {card_str} (計: {score})", False

        elif action_type == "stand":
            hand.status = "stand"
            return f"スタンドしました。(計: {hand.score})", True

        elif action_type == "double":
            if len(hand.cards) != 2:
                raise BlackjackActionError("最初の2枚の時しかダブルダウンできません。")

            # 追加の参加コストを徴収（チップ不足や制限超えは自動的に例外が送出される）
            BetService.validate_bet(uid, hand.bet)
            BetService.escrow(uid, hand.bet)

            hand.bet *= 2
            hand.is_doubled = True

            card = self.deck.draw()
            hand.add_card(card)
            score = hand.score
            card_str = Deck.format_card(card)

            if hand.status == "bust":
                return (
                    f"ダブルダウン！\n参加コストが {hand.bet} pts に倍増。\n引いたカード: {card_str} (計: {score}) -> 💥 バースト！",
                    True,
                )
            else:
                hand.status = "stand"
                return (
                    f"ダブルダウン！\n参加コストが {hand.bet} pts に倍増。\n引いたカード: {card_str} (計: {score}) -> スタンドします。",
                    True,
                )

        elif action_type == "split":
            if len(player.hands) >= 2:
                raise BlackjackActionError("既にスプリット済みです。")
            if len(hand.cards) != 2:
                raise BlackjackActionError("カードが2枚の時しかスプリットできません。")
            if Deck.VALUES[hand.cards[0][1]] != Deck.VALUES[hand.cards[1][1]]:
                raise BlackjackActionError("同じバリューのカードでないとスプリットできません。")

            # 追加の参加コストを徴収（チップ不足や制限超えは自動的に例外が送出される）
            BetService.validate_bet(uid, hand.bet)
            BetService.escrow(uid, hand.bet)

            # 手札を分割
            card1 = hand.cards[0]
            card2 = hand.cards[1]

            # 1枚目を新しい手札（現在の位置）に、2枚目を別の手札にする
            hand.cards = [card1, self.deck.draw()]
            if hand.score == 21:
                hand.status = "stand"

            new_hand = BlackjackHand([card2, self.deck.draw()], hand.bet)
            if new_hand.score == 21:
                new_hand.status = "stand"

            player.add_hand(new_hand)

            return "手札をスプリットしました！追加のカードが配られます。", False

        raise BlackjackActionError("不明なアクション")

    def should_dealer_draw(self) -> bool:
        """ディーラーがさらにカードを引くべきか判定する"""
        score = Deck.get_score(self.dealer_hand)
        return score < 17

    def dealer_draw_step(self) -> str:
        """ディーラーがカードを1枚引く処理を実行し、引いたカードの文字列表現を返す"""
        score = Deck.get_score(self.dealer_hand)

        # 接待ロジック: ディーラーのバースト誘導
        if BlackjackHospitality.apply_dealer_bust_induction(self.deck, self.players, score):
            # 誘導が成功した場合、恩恵を受けた全プレイヤーの手札にフラグを立てる
            for p_dict in self.players:
                uid = p_dict["id"]
                player = self.player_states.get(uid)
                if not player:
                    continue
                for h in player.hands:
                    # 既に役が成立している場合は恩恵（ペナルティ）の対象外とする（JP保護）
                    if not h.get_rare_hand_info()["has_any"]:
                        h.hospitality_triggered = True

        card = self.deck.draw()
        self.dealer_hand.append(card)
        return Deck.format_card(card)

    def dealer_turn(self):
        """
        ディーラーのターンを一括実行する（後方互換用）。
        View側の演出で逐次実行する場合は dealer_draw_step をループ呼び出しする。
        """
        if self.is_dealer_turn_executed:
            return Deck.get_score(self.dealer_hand)
        self.is_dealer_turn_executed = True

        while self.should_dealer_draw():
            self.dealer_draw_step()

        return Deck.get_score(self.dealer_hand)

    def settle_all(self):
        """全員の配当計算"""
        if self.status == "settled":
            return []

        d_score = Deck.get_score(self.dealer_hand)
        results = []

        is_multi = len(self.players) >= 2
        for p in self.players:
            uid = p["id"]
            player = self.player_states[uid]

            total_payout = 0
            user_hands_results = []
            is_any_win = False

            for h_idx, hand in enumerate(player.hands):
                # ルールエンジンで判定
                rule_res = BlackjackRules.calculate_payout(hand, d_score)
                payout_multiplier = rule_res["payout_multiplier"]
                result_str = rule_res["result_str"]
                is_win = rule_res["is_win"]

                # 接待発動時のJP無効化処理
                jackpot_msg = ""
                rare_bonus_msg = ""

                if hand.hospitality_triggered and hand.status != "bust":
                    jackpot_msg = " ✨ **幸運の女神が微笑んでいるようです！**"
                    if rule_res["is_rare"]:
                        jackpot_msg += "\n⚠️ **女神がボーナスを持ち逃げしました…**"
                        # 通常配当(2倍等)に上書き
                        payout_multiplier = BlackjackRules.PAYOUT_RATIO_WIN if is_win else 0
                        result_str = "🎉 Win" if is_win else result_str

                # Payout 実行
                payout = 0
                if payout_multiplier > 0:
                    reason = f"BJ勝利({rule_res['rare_type'] or '通常'})"
                    payout = BetService.payout(
                        uid, int(hand.bet * payout_multiplier), is_pvp=is_multi, reason=reason
                    )

                    # Jackpot 連携
                    if rule_res["jp_rarity"] != JPRarity.NONE and not hand.hospitality_triggered:
                        jp_payout = BetService.execute_jackpot(
                            uid, GameType.BLACKJACK, rule_res["jp_rarity"], rule_res["result_str"]
                        )
                        payout += jp_payout
                        rare_bonus_msg = f" (JP + {int(payout_multiplier)}倍: {payout}pts)"

                    # Suited BJ 特殊ボーナス
                    if rule_res["rare_type"] == "suited_bj" and not hand.hospitality_triggered:
                        jp_bonus = min(1000, wallet.load_balance(BetService.SYSTEM_JACKPOT_ID))
                        if jp_bonus > 0:
                            pool = wallet.load_balance(BetService.SYSTEM_JACKPOT_ID)
                            wallet.save_balance(BetService.SYSTEM_JACKPOT_ID, pool - jp_bonus)
                            wallet.add_history(
                                BetService.SYSTEM_JACKPOT_ID,
                                f"Suited BJ ボーナス to ID:{uid}",
                                -jp_bonus,
                            )
                            BetService.payout(
                                uid, jp_bonus, is_pvp=False, reason="Suited BJ ボーナス"
                            )
                            payout += jp_bonus
                            result_str = "♠️ **Suited Blackjack!** (+1000pts)"

                else:
                    # 負けの場合はJPへ追加
                    BetService.add_to_jackpot(hand.bet)

                # プッシュ（返金）の特殊処理
                if payout_multiplier == BlackjackRules.PAYOUT_RATIO_PUSH:
                    # payoutは上ですでに計算済み(1倍)
                    pass

                total_payout += payout
                if is_win:
                    is_any_win = True

                hand_label = f" (手札{h_idx + 1})" if len(player.hands) > 1 else ""
                user_hands_results.append(
                    {
                        "hand": " ".join([Deck.format_card(c) for c in hand.cards]),
                        "score": hand.score,
                        "result": result_str + hand_label + rare_bonus_msg + jackpot_msg,
                    }
                )

            # 統計更新
            wallet.update_stats(uid, is_any_win, total_payout)

            results.append(
                {
                    "name": p["name"],
                    "hands": user_hands_results,
                    "total_payout": total_payout,
                }
            )

        self.status = "settled"
        return results
