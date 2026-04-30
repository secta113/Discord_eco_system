from typing import Dict, List, Optional, Tuple

from core.utils.logger import Logger

from .pk_exceptions import PokerActionError
from .pk_models import PokerPlayer


class PokerRoundManager:
    """
    ポーカーのベッティングラウンド（プリフロップ、フロップ等）における
    手番管理とアクション処理を担当するクラス。
    """

    def __init__(
        self,
        players: List[Dict],
        player_states: Dict[int, PokerPlayer],
        big_blind: int,
        pot: int = 0,
        current_max_bet: int = 0,
        turn_index: int = 0,
    ):
        self.players = players
        self.player_states = player_states
        self.big_blind = big_blind
        self.pot = pot
        self.current_max_bet = current_max_bet
        self.turn_index = turn_index

    def handle_action(
        self, user_id: int, action: str, amount: int = 0
    ) -> Tuple[bool, Optional[str]]:
        """プレイヤーのアクションを処理し、結果を返す"""
        player = self.player_states.get(user_id)
        if not player:
            raise PokerActionError("プレイヤーが見つかりません。")

        # 実際の消費ポイントをトレースするための変数
        trace_amount = amount
        success = True
        msg = None

        if action == "fold":
            player.fold()
        elif action == "check":
            if player.current_bet < self.current_max_bet:
                raise PokerActionError(
                    f"チェックできません。コール({self.current_max_bet}pts)が必要です。"
                )
            player.is_turn_done = True
        elif action == "call":
            call_amount = self.current_max_bet - player.current_bet
            if call_amount > 0:
                self._collect_bet(user_id, call_amount)
                trace_amount = call_amount
            player.is_turn_done = True
        elif action == "raise":
            try:
                # _handle_raise は成功時に True を返し、失敗時は PokerActionError を投げる
                self._handle_raise(player, amount)
            except PokerActionError as e:
                if player.is_npc:
                    # NPCの場合は不正なレイズ額でもフォールド（ドロップ）せず、コールに差し替えて継続させる
                    call_amount = self.current_max_bet - player.current_bet
                    if call_amount > 0:
                        self._collect_bet(user_id, call_amount)
                    player.is_turn_done = True
                    action = "call"
                    msg = f"レイズ失敗のため自動コールに切り替えました: {e}"
                else:
                    raise e
        elif action == "all_in":
            trace_amount = player.stack
            self._collect_bet(user_id, player.stack)
            self._update_max_bet(player)
            player.is_turn_done = True
            player.status = "all_in"  # is_all_in プロパティが True になる
        else:
            if player.is_npc:
                player.fold()
                trace_amount = 0
                action = "fold"
                success = True
                msg = "無効なアクションのため自動フォールドしました。"
            else:
                raise PokerActionError("無効なアクションです。")

        Logger.info("Poker", f"RoundManager: {action} from {player.name} (actual: {trace_amount})")

        return True, msg

    def _handle_raise(self, player: PokerPlayer, amount: int) -> Tuple[bool, Optional[str]]:
        # 目標とする合計ベット額を決定（指定がなければミニマムレイズ）
        target_total = amount if amount > 0 else (self.current_max_bet + self.big_blind)

        if target_total <= self.current_max_bet:
            raise PokerActionError(
                f"レイズ額は現在の最大ベット({self.current_max_bet})より大きくしてください。"
            )

        add_amount = target_total - player.current_bet
        if add_amount <= 0:
            raise PokerActionError("有効な数値を入力してください。")

        self._collect_bet(player.user_id, add_amount)
        self._update_max_bet(player)
        return True, None

    def _update_max_bet(self, player: PokerPlayer):
        """現在の最大ベット額を更新し、他プレイヤーのアクションフラグをリセットする"""
        if player.current_bet > self.current_max_bet:
            self.current_max_bet = player.current_bet
            # 他のアクティブプレイヤーのアクション済みフラグをリセット
            for p in self.player_states.values():
                if p.status == "playing" and p.user_id != player.user_id and not p.is_all_in:
                    p.is_turn_done = False
        player.is_turn_done = True

    def _collect_bet(self, user_id: int, amount: int):
        player = self.player_states[user_id]
        actual_amount = min(player.stack, amount)

        if actual_amount > 0:
            player.stack -= actual_amount
            player.current_bet += actual_amount
            player.total_bet += actual_amount
            self.pot += actual_amount

    def is_round_over(self) -> bool:
        """現在のベッティングラウンドが終了したか判定"""
        can_act_players = [
            p for p in self.player_states.values() if p.status == "playing" and not p.is_all_in
        ]

        for p in can_act_players:
            if not p.is_turn_done or p.current_bet < self.current_max_bet:
                return False

        return True

    def rotate_turn(self):
        """手番を次の有効なプレイヤーに進める"""
        if not self.players:
            return

        self.turn_index = (self.turn_index + 1) % len(self.players)
        self.ensure_valid_turn()

    def ensure_valid_turn(self):
        """アクション不能なプレイヤーをスキップする"""
        start_index = self.turn_index
        while True:
            uid = self.players[self.turn_index]["id"]
            player = self.player_states[uid]
            if player.status == "playing" and not player.is_all_in:
                break

            self.turn_index = (self.turn_index + 1) % len(self.players)
            if self.turn_index == start_index:
                break
