from logic.bet_service import BetService


class BaseGameSession:
    """
    あらゆる対戦ゲームで流用可能なベースセッションクラス。
    参加募集、エスクロー(預かり金)、手番管理、Pot管理を担当。
    """

    def __init__(self, channel_id, bet_amount):
        self.channel_id = channel_id
        self.bet_amount = bet_amount
        self.status = "recruiting"  # recruiting | playing | settled
        self.pot = 0
        self.players = []  # {'id', 'name', 'mention'}
        self.turn_index = 0

    @property
    def game_type(self) -> str:
        return "base"

    @property
    def game_name(self) -> str:
        return "ゲーム"

    @property
    def min_players(self) -> int:
        return 1

    @property
    def host_id(self) -> int:
        if not self.players:
            return 0
        try:
            return int(self.players[0]["id"])
        except (ValueError, TypeError):
            return 0

    def can_start(self):
        """ゲーム開始可能かチェックする。開始不可の場合は例外を送出。"""
        if len(self.players) < self.min_players:
            from managers.manager import GameActionError

            raise GameActionError(
                f"⚠️ {self.game_name}は{self.min_players}名以上でないと開始できません。"
            )

    def get_join_message(self, user) -> str:
        """参加完了時のメッセージ。ゲームごとにオーバーライド可能。"""
        return f"✅ <@{user.id}> が参加しました。(現在のPot: {self.pot} pts)"

    def add_player(self, user, asset_rank: str = "Standard"):
        """参加処理。二重参加やポイント不足時は例外を送出。"""
        if self.is_user_joined(user.id):
            from managers.manager import GameActionError

            raise GameActionError("⚠️ 既に参加しています。")

        # BetService.escrow が失敗時に InsufficientFundsError を投げるため、呼び出すだけでOK
        BetService.escrow(user.id, self.bet_amount)

        self.players.append(
            {
                "id": user.id,
                "name": user.display_name,
                "mention": f"<@{user.id}>",
                "asset_rank": asset_rank,
            }
        )
        self.pot += self.bet_amount
        return True

    def get_current_player(self):
        """現在の手番のプレイヤーを返す。"""
        if not self.players or self.turn_index >= len(self.players):
            return None
        return self.players[self.turn_index]

    def is_user_joined(self, user_id: int) -> bool:
        """ユーザーが既に参加しているかチェックする。"""
        return any(p["id"] == user_id for p in self.players)

    def rotate_turn(self) -> bool:
        """手番を次に回す。一周したら False を返す。"""
        self.turn_index += 1
        if self.turn_index >= len(self.players):
            return False
        return True

    def loop_rotate_turn(self) -> int:
        """手番を円環状（無限ループ）に回す。ポーカー等で使用。"""
        if not self.players:
            return 0
        self.turn_index = (self.turn_index + 1) % len(self.players)
        return self.turn_index

    def refund_all(self):
        """キャンセル時などに全員に返金する。NPC (ID < 0) は除外。"""
        for p in self.players:
            if p["id"] > 0:
                BetService.payout(p["id"], self.bet_amount)
        self.status = "cancelled"

    def to_dict(self):
        return {
            "channel_id": self.channel_id,
            "bet_amount": self.bet_amount,
            "status": self.status,
            "pot": self.pot,
            "players": self.players,
            "turn_index": self.turn_index,
            "game_type": self.game_type,
            "host_id": self.host_id,
        }

    @classmethod
    def from_dict(cls, data):
        obj = cls(data["channel_id"], data["bet_amount"])
        obj.status = data["status"]
        obj.pot = data["pot"]
        obj.players = data["players"]
        obj.turn_index = data.get("turn_index", 0)
        return obj
