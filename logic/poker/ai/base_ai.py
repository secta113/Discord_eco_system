from typing import Tuple

from logic.poker.pk_models import PokerPlayer
from logic.poker.pk_rules import PokerRules


class PokerAI:
    """
    ポーカーAIの基底（基本）クラス。
    全てのAIランクは本クラスを継承し、decide_action() をオーバーライドして思考ロジックを実装します。
    勝率（ハンドの強さ）計算や、例外のない安全なレイズ処理などの共通ユーティリティを持ちます。
    """

    def __init__(self, player: PokerPlayer):
        self.player = player

    def decide_action(self, session) -> Tuple[str, int]:
        """
        AIの行動（チェック、コール、レイズ、フォールドなど）を決定して返します。

        Args:
            session (TexasPokerService): 現在のゲームセッション状態
        Returns:
            Tuple[str, int]: (アクション名, レイズやベットの目標合計額)
            ※アクション名は "check", "call", "raise", "fold", "all_in" のいずれか
        """
        raise NotImplementedError

    def get_hand_strength(self, session) -> float:
        """
        現在のハンド（手札）の強さと勝率(Equity)を 0.0 ~ 1.0 の間で評価して返します。

        プロセス:
        1. プリフロップ(コミュニティカード0枚)時は、手札の役やスート一致(スーテッド)度合いで暫定評価
        2. フロップ以降は現在の役の強さ + アウツ（今後のドローで逆転できる見込み枚数）を加味して評価
        """
        all_cards = self.player.hole_cards + session.community_cards
        if len(session.community_cards) == 0:
            rank, strength, _ = PokerRules.get_best_hand_provisional(self.player.hole_cards)
            if rank >= 2:
                return 0.5 + (strength[0] / 15.0) * 0.4
            high_card = max(strength) if strength else 0
            is_suited = self.player.hole_cards[0][0] == self.player.hole_cards[1][0]
            base = (high_card / 15.0) * 0.4
            if is_suited:
                base += 0.1
            return min(0.6, 0.1 + base)

        if len(all_cards) < 5:
            rank, strength, _ = PokerRules.get_best_hand_provisional(all_cards)
        else:
            rank, strength, _ = PokerRules.get_best_hand(all_cards)

        rank_base = {1: 0.1, 2: 0.3, 3: 0.5, 4: 0.6, 5: 0.7, 6: 0.8, 7: 0.9}
        score = rank_base.get(rank, 1.0)
        if strength:
            score += (strength[0] / 15.0) * 0.1

        if len(session.community_cards) < 5:
            outs = PokerRules.get_outs_count(all_cards)
            score += outs * 0.025

        return min(1.0, score)

    def _should_fold_guard(
        self, session, action: str, amount: int, strength_threshold: float = 0.2
    ) -> bool:
        """
        プリフロップにおいて、少額のコールであればフォールドを阻止すべきか判定します。
        """
        if action != "fold" or len(session.community_cards) > 0:
            return False

        needed = session.current_max_bet - self.player.current_bet
        # ビッグブラインド以下の支払いであれば、一定以上の手札強度があれば続行(call)させる
        if needed <= session.big_blind:
            if self.get_hand_strength(session) >= strength_threshold:
                return True
        return False

    def _safe_raise(self, session, target_amount: int) -> Tuple[str, int]:
        """
        引数で指定された額まで安全にレイズを検討します。
        AIの手持ちスタックが目標額に満たない場合、自動的に "all_in" へフォールバックします。
        また、指定額が現在のミニマムレイズに満たない場合は、不成立として "fold" を返します（安全策）。
        """
        min_raise = session.current_max_bet + session.big_blind
        if target_amount < min_raise:
            # レイズ額不足時はフォールドせず、コール（またはチェック）にフォールバックして勝機を逃さないようにする
            needed = session.current_max_bet - self.player.current_bet
            if needed <= 0:
                return "check", 0
            if needed >= self.player.stack:
                return "all_in", 0
            return "call", 0

        needed = target_amount - self.player.current_bet
        if needed >= self.player.stack:
            return "all_in", 0
        return "raise", target_amount
