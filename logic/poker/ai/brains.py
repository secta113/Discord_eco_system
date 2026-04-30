import random
from itertools import combinations
from typing import Tuple

from core.utils.logger import Logger
from logic.poker.pk_deck import PokerDeck
from logic.poker.pk_rules import PokerRules

from .base_ai import PokerAI
from .personality import apply_personality


class TrashAI(PokerAI):
    """
    【雑魚AI (カモ/養分)】
    基本的にどんな手札でもコールしてくる（ゲームを回すためのポイント供給源）。
    コミュニティカードが開くにつれて、大きなベットに対してはランダムに降りることもある。
    """

    def decide_action(self, session) -> Tuple[str, int]:
        needed = session.current_max_bet - self.player.current_bet
        action, amt = "call", 0
        if needed == 0:
            action, amt = "check", 0
        elif len(session.community_cards) > 0 and random.random() >= 0.85:
            action, amt = "fold", 0

        action, amt = apply_personality(action, amt, session, self.player)

        # プリフロップ・フォールドガードの適用
        if self._should_fold_guard(session, action, amt, strength_threshold=0.15):
            action, amt = "call", 0

        return action, amt


class CommonAI(PokerAI):
    """
    【標準的な一般市民AI】
    極端な無謀さはないが、少しでも可能性があると追いかけてしまう消極的な初心者思考。
    手札の強さが0.4以上ならコールするが、それ以下だとベット額を見て降りるか決める。
    """

    def decide_action(self, session) -> Tuple[str, int]:
        strength = self.get_hand_strength(session)
        needed = session.current_max_bet - self.player.current_bet

        if needed == 0:
            action, amt = "check", 0
        elif strength > 0.4:
            action, amt = "call", 0
        elif needed <= session.big_blind:
            action, amt = ("call", 0) if random.random() < 0.5 else ("fold", 0)
        else:
            action, amt = ("call", 0) if random.random() < 0.3 else ("fold", 0)

        action, amt = apply_personality(action, amt, session, self.player)

        # プリフロップ・フォールドガード
        if self._should_fold_guard(session, action, amt, strength_threshold=0.25):
            action, amt = "call", 0

        return action, amt


class RareAI(PokerAI):
    """
    【少しは学習した中級者AI】
    ある程度の勝率(>0.7)があればレイズを仕掛けてくる。
    中程度の勝率(>0.3)の場合でも、あまりに相手のベットが額が大きいとしっかり降りる冷静さを持つ。
    """

    def decide_action(self, session) -> Tuple[str, int]:
        strength = self.get_hand_strength(session)
        needed = session.current_max_bet - self.player.current_bet

        if needed == 0:
            action, amt = "check", 0
        elif strength > 0.7:
            if random.random() < 0.4:
                action, amt = self._safe_raise(session, session.current_max_bet + session.big_blind)
            else:
                action, amt = "call", 0
        elif strength > 0.3:
            if needed > session.big_blind * 3:
                action, amt = ("call", 0) if random.random() < 0.4 else ("fold", 0)
            else:
                action, amt = "call", 0
        else:
            if needed <= session.big_blind:
                action, amt = ("call", 0) if random.random() < 0.5 else ("fold", 0)
            else:
                action, amt = ("call", 0) if random.random() < 0.2 else ("fold", 0)

        action, amt = apply_personality(action, amt, session, self.player)

        # プリフロップ・フォールドガード
        if self._should_fold_guard(session, action, amt, strength_threshold=0.2):
            action, amt = "call", 0

        return action, amt


class LegendaryAI(PokerAI):
    """
    【非常に強い戦術的AI】
    ポットオッズとエクイティ(勝率)の計算に基づいて合理的な判断を下す。
    強い役を確信した時は強烈なレイズを叩き込み、無駄な支払いを避ける上級者。
    """

    def decide_action(self, session) -> Tuple[str, int]:
        action, amt = self._get_base_action(session)
        action, amt = apply_personality(action, amt, session, self.player)

        # プリフロップ・フォールドガード
        if self._should_fold_guard(session, action, amt, strength_threshold=0.3):
            action, amt = "call", 0

        return action, amt

    def _get_base_action(self, session) -> Tuple[str, int]:
        strength = self.get_hand_strength(session)
        needed = session.current_max_bet - self.player.current_bet

        if needed == 0:
            if strength > 0.7 or (strength > 0.4 and random.random() < 0.2):
                return self._safe_raise(session, session.big_blind * 2)
            else:
                return "check", 0

        pot_odds = needed / (session.pot + needed)
        equity = strength * 0.8
        # プリフロップ(Turn 0)では勝率計算が厳しく出やすいため、少し緩和して参加率を上げる
        is_preflop = len(session.community_cards) == 0
        effective_pot_odds = pot_odds * 0.7 if is_preflop else pot_odds

        if equity > effective_pot_odds:
            if strength > 0.8:
                return self._safe_raise(session, session.current_max_bet + session.big_blind * 3)
            else:
                return "call", 0
        elif random.random() < 0.1:
            return self._safe_raise(session, session.current_max_bet + session.big_blind)
        elif (needed <= session.big_blind) and (random.random() < 0.3 or is_preflop):
            # プリフロップならBB以下は原則降りない(ブラフ以外でも)
            return "call", 0
        else:
            return "fold", 0


class MonsterAI(LegendaryAI):
    """
    【最凶のお仕置きAI】
    LegendaryAI の賢い判断アルゴリズムに加え、「イカサマ」能力を持つ。
    - 他のプレイヤーの手札を透視し、自分が負けていると知ると超高額なブラフを仕掛ける
    - 一定確率で、デッキの中から「自分を勝たせる都合の良いカード」を探し出し、自分の手札とすり替える (cheat_hand)

    実装メモ:
        プレイヤーがレア役(ジャックポット対象のRank8以上)を持っている場合は空気を読んで絶対にお仕置き(イカサマ)をしない接待仕様。
    """

    def decide_action(self, session) -> Tuple[str, int]:
        comm_cards = [tuple(c) for c in session.community_cards]
        best_human_rank = 0
        has_jackpot_user = False

        for p in session.player_states.values():
            if not p.is_npc and p.status == "playing":
                rank = self._get_player_rank(p, comm_cards)
                if rank >= 8:
                    has_jackpot_user = True
                best_human_rank = max(best_human_rank, rank)

        my_rank = self._get_player_rank(self.player, comm_cards)

        # 接待：Primeユーザーが参加している場合はレイズ（お仕置き）率を上げる
        has_prime_opponent = any(
            p.asset_rank == "Prime" and p.status == "playing"
            for p in session.player_states.values()
            if not p.is_npc
        )
        raise_chance = 0.85 if has_prime_opponent else 0.7

        if not has_jackpot_user and my_rank <= best_human_rank:
            # フェーズに応じて「お仕置き（ブラフ/プレッシャー）」の頻度を変える
            is_early = session.phase in ["pre_flop", "flop"]
            # 序盤は 40%, 後半は 70-85% の確率で仕掛ける
            effective_raise_chance = (raise_chance * 0.5) if is_early else raise_chance

            if random.random() < effective_raise_chance:
                multiplier = self._get_bluff_multiplier()
                return self._safe_raise(
                    session, session.current_max_bet + int(session.big_blind * multiplier)
                )

        # MonsterAIは性格補正(apply_personality)をバイパスし、常に純粋なロジックで動く
        action, amt = self._get_base_action(session)

        # MonsterAIとしての意地: 人間がJP対象(Rank 8以上)でない限り、リバーのイカサマまで生き残るために絶対に降りない
        if action == "fold" and not has_jackpot_user:
            return self._handle_fold_denial(session)

        action, amt = apply_personality(action, amt, session, self.player)

        # プリフロップ・フォールドガード (MonsterAIはさらに強気)
        if self._should_fold_guard(session, action, amt, strength_threshold=0.1):
            action, amt = "call", 0

        return action, amt

    def cheat_hand(self, session):
        """
        一定確率で、デッキの中から自分を勝たせるカードを探して手札をすり替える。
        """
        if random.random() < 0.4:
            return

        comm_cards = [tuple(c) for c in session.community_cards]

        # 接待：誰かがJP対象(Rank8以上)の手札を持っている場合は絶対にイカサマしない
        for p in session.player_states.values():
            if not p.is_npc and p.status == "playing":
                if self._get_player_rank(p, comm_cards) >= 8:
                    return

        # 最強の対戦相手を特定
        strongest_opp, max_opp_rank = self._get_strongest_opponent(session, comm_cards)
        my_rank = self._get_player_rank(self.player, comm_cards)

        # 接待：最強の対戦相手が Recovery ユーザーの場合は勝ちを譲る
        if self._should_skip_for_recovery(strongest_opp, max_opp_rank, my_rank):
            return

        if my_rank <= max_opp_rank:
            # 山札（デッキ）にあるカードのみを使用可能カードとする
            available_cards = [tuple(c) for c in session.deck.cards]
            if not available_cards:
                return

            best_cheat_cards, best_cheat_rank = self._find_best_cheat_hand(
                available_cards, comm_cards
            )

            if best_cheat_cards:
                self._execute_swap_with_deck(session, best_cheat_cards)
                Logger.info(
                    "PokerAI_Cheat",
                    f"MonsterAI '{self.player.name}' swapped cards with deck! rank:{best_cheat_rank}, old_rank:{my_rank}, opponent_max:{max_opp_rank}",
                )
            else:
                self._execute_fallback_cheat(session)

    def _get_player_rank(self, player, comm_cards):
        """指定されたプレイヤーの現在の役ランクを取得する"""
        cards = [tuple(c) for c in player.hole_cards] + comm_cards
        rank, _, _ = (
            PokerRules.get_best_hand(cards)
            if len(cards) >= 5
            else PokerRules.get_best_hand_provisional(cards)
        )
        return rank

    def _get_bluff_multiplier(self) -> int:
        """ブラフ用のレイズ倍率を決定する"""
        roll = random.random()
        if roll < 0.3:
            # 最小レイズ(+1BB)より少し強気の 2倍
            return 2
        elif roll < 0.7:
            # 3〜5倍の範囲でランダム
            return random.randint(3, 5)
        # 性性格補正込みで 5〜8倍
        return 5 + int(getattr(self.player, "risk_level", 0.5) * 3)

    def _handle_fold_denial(self, session) -> Tuple[str, int]:
        """フォールドを拒否して継続する際の挙動"""
        needed = session.current_max_bet - self.player.current_bet
        if needed >= self.player.stack:
            return "all_in", 0
        if random.random() < 0.6:
            return "call", 0
        return self._safe_raise(session, session.current_max_bet + session.big_blind * 2)

    def _get_strongest_opponent(self, session, comm_cards):
        """最強の対戦相手とそのランクを取得する"""
        strongest_player = None
        max_rank = 0
        for p in session.player_states.values():
            if p.user_id != self.player.user_id and p.status == "playing":
                rank = self._get_player_rank(p, comm_cards)
                if rank > max_rank or strongest_player is None:
                    max_rank = rank
                    strongest_player = p
        return strongest_player, max_rank

    def _should_skip_for_recovery(self, strongest_opp, max_opp_rank, my_rank) -> bool:
        """Recoveryユーザーへの接待としてイカサマを中止すべきか判定"""
        if strongest_opp and not strongest_opp.is_npc and strongest_opp.asset_rank == "Recovery":
            if max_opp_rank >= my_rank:
                Logger.info(
                    "PokerAI_Cheat",
                    f"MonsterAI '{self.player.name}' skipped cheat for Recovery user '{strongest_opp.name}'",
                )
                return True
        return False

    def _find_best_cheat_hand(self, available_cards, comm_cards):
        """山札の中から、現在のランクを上回る最強の組み合わせを探す"""
        best_cards = None
        best_rank = -1
        best_strength = []

        for combo in combinations(available_cards, 2):
            test_cards = list(combo) + comm_cards
            rank, strength, _ = PokerRules.get_best_hand(test_cards)

            if rank > 9:  # 接待：ロイヤルは出さない
                continue

            if rank > best_rank or (rank == best_rank and strength > best_strength):
                best_rank = rank
                best_strength = strength
                best_cards = list(combo)

        return best_cards, best_rank

    def _execute_swap_with_deck(self, session, new_hand):
        """手札と山札の物理的な入れ替えを実行し、整合性を保つ"""
        old_hand = self.player.hole_cards
        self.player.hole_cards = [list(c) for c in new_hand]

        # デッキから新しいカードを削除
        for c in new_hand:
            target = list(c)
            for i, dc in enumerate(session.deck.cards):
                if list(dc) == target:
                    session.deck.cards.pop(i)
                    break

        # 古いカードをデッキに戻す
        for c in old_hand:
            session.deck.cards.append(list(c))

        session.deck.shuffle()

    def _execute_fallback_cheat(self, session):
        """より良い組み合わせが見つからなかった場合のフォールバック挙動"""
        if len(session.deck.cards) >= 2:
            old_hand = self.player.hole_cards
            new_hand = [session.deck.draw(), session.deck.draw()]
            self.player.hole_cards = [list(c) for c in new_hand]
            for c in old_hand:
                session.deck.cards.append(list(c))
            session.deck.shuffle()
            Logger.info("PokerAI_Cheat", f"MonsterAI '{self.player.name}' used deck fallback.")
        else:
            suits = PokerDeck.SUITS
            self.player.hole_cards = [[suits[0], "A"], [suits[1], "A"]]
            Logger.info(
                "PokerAI_Cheat", f"MonsterAI '{self.player.name}' used absolute fallback AA."
            )
