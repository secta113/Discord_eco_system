from core.economy import wallet
from core.handlers.storage import ISessionRepository, SQLiteSessionRepository
from core.utils.logger import Logger

# 変更: 統合された BlackjackService のみをインポート
from logic.bet_service import BetService
from logic.blackjack import BlackjackService
from logic.chinchiro import ChinchiroService
from logic.dobumon.dob_battle.battle_session import DobumonBattleSession
from logic.economy.status import StatusService
from logic.match_service import MatchService
from logic.poker.pk_service import TexasPokerService


class GameActionError(Exception):
    """ゲーム進行上の既定エラー"""

    pass


class GameManager:
    def __init__(self, session_repo: ISessionRepository):
        self.session_repo = session_repo

    def _validate_new_creation(self, channel_id):
        if self.get_session(channel_id):
            raise GameActionError("⚠️ 現在このチャンネルで別のゲームが進行中です。")

    def _validate_joinable(self, session, user):
        if not session or session.status != "recruiting":
            raise GameActionError("⚠️ 現在募集中のゲームはありません。")
        if any(p["id"] == user.id for p in session.players):
            raise GameActionError("⚠️ 既に参加しています。")

    def _try_payment(self, user, amount):
        # BetService.escrow が失敗時に InsufficientFundsError を投げるため、呼び出すだけでOK
        BetService.escrow(user.id, amount)

    def _validate_bet_limit(self, user, amount):
        # BetService.validate_bet が失敗時に例外を投げるため、呼び出すだけでOK
        BetService.validate_bet(user.id, amount)

    # --- セッション管理 (Public) ---
    def get_session(self, channel_id: int):
        data_model = self.session_repo.get_session(channel_id)
        if not data_model:
            return None

        # Pydanticモデルから辞書に変換して既存のfrom_dictに渡す (移行のステップ)
        data = data_model.model_dump()

        game_type = data.get("game_type")
        service_map = {
            "chinchiro": ChinchiroService,
            "blackjack": BlackjackService,
            "match": MatchService,
            "poker": TexasPokerService,
            "dobumon_battle": DobumonBattleSession,
        }

        service_cls = service_map.get(game_type)
        if service_cls:
            return service_cls.from_dict(data)
        return None

    def save_session(self, session):
        # 既存の session.to_dict() を UserSchema 等の対応するモデルに変換する必要があるが、
        # session.to_dict() が返す構造が SessionSchemaType と一致していれば validate_python できる。
        from pydantic import TypeAdapter

        from core.models.validation import SessionSchemaType

        adapter = TypeAdapter(SessionSchemaType)
        model = adapter.validate_python(session.to_dict())
        self.session_repo.save_session(model)
        Logger.info(
            "Session",
            f"Saved: {session.game_type} in channel:{session.channel_id} (Status: {session.status})",
        )

    def get_all_sessions(self):
        """
        保存されているすべてのセッションを復元して返します（起動時の復旧用）。
        """
        all_models = self.session_repo.get_all_sessions()
        sessions = []

        service_map = {
            "chinchiro": ChinchiroService,
            "blackjack": BlackjackService,
            "match": MatchService,
            "poker": TexasPokerService,
            "dobumon_battle": DobumonBattleSession,
        }

        for channel_id, model in all_models.items():
            data = model.model_dump()
            game_type = data.get("game_type")
            service_cls = service_map.get(game_type)
            if service_cls:
                try:
                    sessions.append(service_cls.from_dict(data))
                except Exception as e:
                    Logger.error("Session", f"Failed to restore session in {channel_id}: {e}")
        return sessions

    def update_session(self, channel_id, user):
        """非推奨 (join_sessionを使用)"""
        pass

    def join_session(self, channel_id, user):
        session = self.get_session(channel_id)
        self._validate_joinable(session, user)

        # エスクロー前にランクを取得（共通化）
        asset_rank = StatusService.get_user_status(user.id)

        # ベット上限チェック (ポーカーの場合は buyin_amount を、それ以外は bet_amount を使用)
        validate_amount = session.bet_amount
        if session.game_type == "poker":
            wallet_balance = wallet.load_balance(user.id)
            validate_amount = min(wallet_balance, getattr(session, "buyin_amount", 0))

        try:
            self._validate_bet_limit(user, validate_amount)
        except GameActionError as e:
            if session.game_type == "poker":
                limit = StatusService.get_bet_limit(user.id)
                raise GameActionError(
                    f"{e}\n💡 ポーカー（ランク：{StatusService.get_user_status(user.id)}）のこの卓に参加するには、スタック（持ち点）を {limit} pts 以下にする必要があります。現在の設定（BB {session.bet_amount} pts / Buy-in {getattr(session, 'buyin_amount', 0)} pts）では参加できません。"
                )
            raise e

        # 参加処理（二重参加やコスト不足は自動的に例外が送出される）
        session.add_player(user, asset_rank=asset_rank)
        self.save_session(session)
        # 成功メッセージを返す
        return session.get_join_message(user)

    def end_session(self, channel_id):
        self.session_repo.delete_session(channel_id)
        Logger.info("Session", f"Ended: channel:{channel_id}")

    # --- 各ゲーム作成メソッド ---

    def create_chinchiro(self, channel_id, user, bet_amount):
        try:
            self._validate_new_creation(channel_id)

            # ベット上限チェック
            self._validate_bet_limit(user, bet_amount)

            # チンチロはadd_player内で支払いを行う
            session = ChinchiroService(channel_id, bet_amount)

            # エスクロー前にランクを取得
            asset_rank = StatusService.get_user_status(user.id)

            session.add_player(user, asset_rank=asset_rank)

            self.save_session(session)
            return session, "success"
        except GameActionError as e:
            return None, str(e)

    def create_match(self, channel_id, user, bet_amount):
        try:
            self._validate_new_creation(channel_id)

            # ベット上限チェック
            self._validate_bet_limit(user, bet_amount)

            session = MatchService(channel_id, bet_amount, user)

            # エスクロー前にランクを取得
            asset_rank = StatusService.get_user_status(user.id)

            session.add_player(user, asset_rank=asset_rank)

            self.save_session(session)
            return session, "success"
        except GameActionError as e:
            return None, str(e)

    # 統合されたブラックジャック作成メソッド
    def create_blackjack(self, channel_id, user, bet_amount):
        try:
            self._validate_new_creation(channel_id)

            # ベット上限チェック
            self._validate_bet_limit(user, bet_amount)

            session = BlackjackService(channel_id, bet_amount)

            # エスクロー前にランクを取得
            asset_rank = StatusService.get_user_status(user.id)

            session.add_player(user, asset_rank=asset_rank)

            self.save_session(session)
            return session, "success"
        except GameActionError as e:
            return None, str(e)

    def create_poker(self, channel_id, user, bet_amount, buyin_amount=None, target_player_count=6):
        try:
            self._validate_new_creation(channel_id)

            # バイイン上限チェック
            actual_buyin = buyin_amount if buyin_amount is not None else bet_amount * 20
            # 所持金がバイイン額を下回る場合は所持金全額がスタックになる（ショートバイイン）が、
            # 上限チェックは「入れようとした額」で行う。
            try:
                self._validate_bet_limit(user, actual_buyin)
            except GameActionError as e:
                limit = StatusService.get_bet_limit(user.id)
                max_bb = limit // 20
                status = StatusService.get_user_status(user.id)
                raise GameActionError(
                    f"{e}\n💡 ポーカー（ランク：{status}）では、スタック上限は {limit} pts です。bet額を {max_bb} pts 以下に下げて再度募集してください。"
                )

            session = TexasPokerService(channel_id, bet_amount, buyin_amount, target_player_count)

            # エスクロー前にランクを取得
            asset_rank = StatusService.get_user_status(user.id)

            session.add_player(user, asset_rank=asset_rank)

            self.save_session(session)
            return session, "success"
        except GameActionError as e:
            return None, str(e)

    def create_dobumon_battle(
        self,
        channel_id,
        user,
        attacker,
        defender,
        steps,
        winner_id,
        loser_id,
        battle_type="challenge",
    ):
        try:
            self._validate_new_creation(channel_id)
            session = DobumonBattleSession(channel_id)
            session.attacker_data = attacker.to_dict()
            session.defender_data = defender.to_dict()
            session.steps = steps
            session.winner_id = winner_id
            session.loser_id = loser_id
            session.battle_type = battle_type
            session.status = "playing"

            # 参加者登録
            asset_rank = StatusService.get_user_status(user.id)
            session.players.append(
                {
                    "id": user.id,
                    "name": user.display_name,
                    "mention": f"<@{user.id}>",
                    "asset_rank": asset_rank,
                }
            )

            # PvPの場合は相手も登録
            if battle_type == "challenge" and defender.owner_id:
                target_id = int(defender.owner_id)
                session.players.append(
                    {
                        "id": target_id,
                        "name": defender.name + "(Owner)",
                        "mention": f"<@{target_id}>",
                        "asset_rank": "Standard",
                    }
                )

            self.save_session(session)
            return session, "success"
        except GameActionError as e:
            return None, str(e)


game_manager = GameManager(SQLiteSessionRepository())
