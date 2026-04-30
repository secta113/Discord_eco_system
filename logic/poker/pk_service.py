import asyncio
import json
import os
import random
from typing import Dict, List, Optional

from core.economy import wallet
from core.utils.logger import Logger
from logic.bet_service import BetService
from logic.economy.status import StatusService
from managers.game_session import BaseGameSession

from .ai import get_ai_instance
from .pk_deck import PokerDeck
from .pk_exceptions import (
    PokerActionError,
    PokerError,
    PokerInsufficientStackError,
    PokerTurnError,
)
from .pk_models import PokerPlayer
from .pk_round_manager import PokerRoundManager
from .pk_settlement_manager import PokerSettlementManager


class TexasPokerService(BaseGameSession):
    """
    テキサス・ホールデムのゲーム管理クラス。
    セッション管理とフェーズ遷移を担当し、詳細なロジックは各マネージャーに委譲する。
    """

    PHASES = ["pre_flop", "flop", "turn", "river", "showdown"]

    def __init__(self, channel_id, bet_amount, buyin_amount=None, target_player_count=4):
        super().__init__(channel_id, bet_amount)
        self.big_blind = bet_amount
        self.small_blind = max(1, bet_amount // 2)
        self.buyin_amount: int = buyin_amount if buyin_amount is not None else self.big_blind * 20
        self.target_player_count = min(5, max(1, target_player_count))

        self.deck = PokerDeck()
        self.community_cards: List[tuple[str, str]] = []
        self.player_states: Dict[int, PokerPlayer] = {}
        self.phase: str = "pre_flop"
        self.current_max_bet: int = 0
        self.button_index: int = 0
        self.table_average_stack: float = 0.0
        self.game_rank: str = "common"
        self.npc_blueprints: List[dict] = []
        Logger.info(
            "Poker",
            f"Session initialized: BB={self.big_blind}, SB={self.small_blind}, Buyin={self.buyin_amount}",
        )

    @property
    def game_type(self) -> str:
        return "poker"

    @property
    def game_name(self) -> str:
        return "テキサス・ホールデム"

    def get_join_message(self, user) -> str:
        player = self.player_states.get(user.id)
        stack_amount = getattr(player, "stack", 0) if player else 0
        return f"✅ <@{user.id}> が参加しました。(持ち点: {stack_amount} pts)"

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "buyin_amount": self.buyin_amount,
                "deck": {"cards": self.deck.cards},
                "community_cards": self.community_cards,
                "player_states": {str(k): v.to_dict() for k, v in self.player_states.items()},
                "phase": self.phase,
                "current_max_bet": self.current_max_bet,
                "button_index": self.button_index,
                "table_average_stack": self.table_average_stack,
                "target_player_count": self.target_player_count,
                "game_rank": self.game_rank,
                "npc_blueprints": self.npc_blueprints,
            }
        )
        return data

    @classmethod
    def from_dict(cls, data):
        bet_amount = data.get("bet_amount", 100)
        buyin_amount = data.get("buyin_amount", bet_amount * 20)

        obj = cls(data["channel_id"], bet_amount, buyin_amount)
        obj.status = data["status"]
        obj.pot = data["pot"]
        obj.players = data["players"]
        obj.turn_index = data.get("turn_index", 0)

        obj.big_blind = bet_amount
        obj.small_blind = max(1, bet_amount // 2)

        deck_obj = PokerDeck()
        if "deck" in data and "cards" in data["deck"]:
            deck_obj.cards = data["deck"]["cards"]
        obj.deck = deck_obj

        obj.community_cards = data.get("community_cards", [])
        states = data.get("player_states", {})
        obj.player_states = {int(k): PokerPlayer.from_dict(v) for k, v in states.items()}
        obj.phase = data.get("phase", "pre_flop")
        obj.current_max_bet = data.get("current_max_bet", 0)
        obj.button_index = data.get("button_index", 0)
        obj.table_average_stack = data.get("table_average_stack", 0.0)
        obj.target_player_count = data.get("target_player_count", 6)
        obj.game_rank = data.get("game_rank", "common")
        obj.npc_blueprints = data.get("npc_blueprints", [])
        return obj

    def add_player(self, user, asset_rank: Optional[str] = None) -> bool:
        if self.is_user_joined(user.id):
            from managers.manager import GameActionError

            raise GameActionError("⚠️ 既に参加しています。")

        wallet_balance = wallet.load_balance(user.id)
        actual_buyin = min(wallet_balance, self.buyin_amount)

        # BetService.escrow が失敗時に InsufficientFundsError を投げるため、呼び出すだけでOK
        BetService.escrow(user.id, actual_buyin)

        self.players.append(
            {
                "id": user.id,
                "name": user.display_name,
                "mention": f"<@{user.id}>",
                "asset_rank": asset_rank or StatusService.get_user_status(user.id),
            }
        )
        # 引数で渡されていない場合のみ動的に取得（フォールバック）
        if not asset_rank:
            asset_rank = StatusService.get_user_status(user.id)

        self.player_states[user.id] = PokerPlayer(
            user.id, user.display_name, stack=actual_buyin, asset_rank=asset_rank
        )
        return True

    def refund_all(self):
        for p in self.player_states.values():
            if p.is_npc:
                continue  # NPCへの返金はしない（仮想スタックのため）
            total_refund = p.stack + p.total_bet
            if total_refund > 0:
                BetService.payout(p.user_id, total_refund, reason="ポーカー強制終了による全額返還")
        self.status = "cancelled"

    def start_game(self, button_index: Optional[int] = None):
        self.status = "playing"
        self.phase = "pre_flop"

        # NPC補充がある場合、テーブルの構成設計図を決定
        needed = min(self.target_player_count - len(self.players), 3)
        if needed > 0 and not self.npc_blueprints:
            self._decide_table_blueprint(needed)

        # NPCの自動補充
        self._fill_npcs()
        random.shuffle(self.players)
        num_players = len(self.players)

        # 親（Button）の決定
        if button_index is not None:
            self.button_index = button_index
        else:
            self.button_index = random.randint(0, num_players - 1)

        for p in self.players:
            self.player_states[p["id"]].hole_cards = [self.deck.draw(), self.deck.draw()]

        if num_players == 2:
            sb_idx, bb_idx = self.button_index, (self.button_index + 1) % num_players
        else:
            sb_idx, bb_idx = (
                (self.button_index + 1) % num_players,
                (self.button_index + 2) % num_players,
            )

        # ブラインド徴収（PokerRoundManagerの共有ロジックを利用）
        mgr = self._get_round_manager()
        mgr._collect_bet(self.players[sb_idx]["id"], self.small_blind)
        mgr._collect_bet(self.players[bb_idx]["id"], self.big_blind)

        # 状態を同期
        self.pot = mgr.pot
        self.current_max_bet = mgr.current_max_bet = self.big_blind
        self.turn_index = (bb_idx + 1) % num_players

        mgr.turn_index = self.turn_index
        mgr.ensure_valid_turn()
        self.turn_index = mgr.turn_index

        # Calc table average stack
        total_stack = sum(p.stack for p in self.player_states.values() if p.status == "playing")
        active_count = len([p for p in self.player_states.values() if p.status == "playing"])
        self.table_average_stack = total_stack / active_count if active_count > 0 else 0.0

        Logger.info(
            "Poker",
            f"Game started with {len([p for p in self.player_states.values() if p.is_npc])} NPCs. Total: {num_players}",
        )

    def _fill_npcs(self):
        """不足しているプレイヤー枠をNPCで埋める"""
        current_count = len(self.players)
        if current_count >= self.target_player_count:
            return

        # NPC補充は最大3人までに制限（インフレ抑制）
        needed = min(self.target_player_count - current_count, 3)

        # 設計図がない場合（あるいは再開時）に備えて再判定
        if not self.npc_blueprints or len(self.npc_blueprints) < needed:
            self._decide_table_blueprint(needed)

        # 名前リストの読み込み（data/npc_names.json）
        name_list = ["Bot"]
        name_path = os.path.join("data", "npc_names.json")
        try:
            with open(name_path, "r", encoding="utf-8") as f:
                name_list = json.load(f).get("names", ["Bot"])
        except Exception:
            pass

        # 既に参加している名前は除外（重複回避）
        existing_names = {p["name"] for p in self.players}
        available_names = [n for n in name_list if n not in existing_names]
        if not available_names:
            available_names = name_list
        random.shuffle(available_names)

        for i in range(needed):
            # 設計図からランクと性格を取得
            blueprint = (
                self.npc_blueprints[i]
                if i < len(self.npc_blueprints)
                else {"rank": "common", "personality": None}
            )
            rank_from_bp = blueprint.get("rank")
            if rank_from_bp:
                chosen_rank = rank_from_bp
            else:
                # 性格と同様に、設計図に指定がない場合はランダム（Monster以外から抽選）
                chosen_rank = random.choices(
                    ["legendary", "rare", "common", "trash"], weights=[20, 35, 30, 15]
                )[0]
            fixed_personality = blueprint.get("personality")

            personality_risk_val = random.uniform(0.1, 0.9)

            npc_name = available_names[i % len(available_names)]
            npc_id = -(len(self.player_states) + 1)  # 負数IDを割り当て

            # NPCはシステムからバイインを生成（Jackpotは削らない）
            self.players.append({"id": npc_id, "name": npc_name, "mention": npc_name})

            if fixed_personality:
                personality = fixed_personality
            else:
                personality = random.choice(
                    ["aggressive", "timid", "calculated", "normal", "bluffer", "station", "shark"]
                )

            if chosen_rank == "monster" and personality == "timid":
                personality = "normal"

            risk_level = random.uniform(0.1, 0.9)
            self.player_states[npc_id] = PokerPlayer(
                npc_id,
                npc_name,
                stack=self.buyin_amount,
                is_npc=True,
                ai_rank=chosen_rank,
                personality=personality,
                risk_level=risk_level,
            )
            Logger.info(
                "Poker",
                f"Added NPC: {npc_name} (Rank: {chosen_rank}, Personality: {personality}, Risk: {risk_level:.2f})",
            )

    def handle_action(self, user_id: int, action: str, amount: int = 0):
        current_p = self.get_current_player()
        if not current_p or user_id != current_p["id"]:
            raise PokerTurnError()

        mgr = self._get_round_manager()
        success, msg = mgr.handle_action(user_id, action, amount)
        # handle_action 自体は内部で例外を投げるように変更済みだが、
        # 万が一 NPC の自動フォールドなどで False が返るケースに備えて一応残す
        # (実際には pk_round_manager.py は常に True か例外を返すように修正した)

        # 状態の同期
        self.pot = mgr.pot
        self.current_max_bet = mgr.current_max_bet
        self.turn_index = mgr.turn_index

        if mgr.is_round_over():
            self._next_phase()
            if self.phase == "showdown":
                return True, "ベッティング終了。ショウダウンへ移行します。"

            phase_names = {"flop": "フロップ", "turn": "ターン", "river": "リバー"}
            return (
                True,
                f"全員のベットが完了しました。**{phase_names.get(self.phase, self.phase)}** が配られます。",
            )

        mgr.rotate_turn()
        self.turn_index = mgr.turn_index
        return True, "アクション完了"

    def _get_round_manager(self) -> PokerRoundManager:
        return PokerRoundManager(
            self.players,
            self.player_states,
            self.big_blind,
            self.pot,
            self.current_max_bet,
            self.turn_index,
        )

    def _next_phase(self):
        if self.phase == "showdown":
            return

        for p in self.player_states.values():
            p.reset_round_bet()
        self.current_max_bet = 0

        old_phase = self.phase
        if self.phase == "pre_flop":
            self.phase = "flop"
            self.community_cards.extend([self.deck.draw(), self.deck.draw(), self.deck.draw()])
        elif self.phase == "flop":
            self.phase = "turn"
            self.community_cards.append(self.deck.draw())
        elif self.phase == "turn":
            self.phase = "river"
            self.community_cards.append(self.deck.draw())
        elif self.phase == "river":
            self.phase = "showdown"
            return

        # 次フェーズの開始手番設定
        self.turn_index = (self.button_index + 1) % len(self.players)
        mgr = self._get_round_manager()
        mgr.ensure_valid_turn()
        self.turn_index = mgr.turn_index

        # アクティブプレイヤーが1人以下なら即座に次フェーズへ
        active_p = [
            p for p in self.player_states.values() if p.status == "playing" and not p.is_all_in
        ]
        if len(active_p) <= 1:
            self._next_phase()

    def settle_game(self):
        if self.status == "settled":
            return [], 0

        settler = PokerSettlementManager(self.community_cards, self.pot)
        # winners, active_playersなどの詳細な特定はSettlementManager内部で行う
        # 参加人数は全プレイヤー数(player_statesの長さ)とする
        settle_details, rake_amount = settler.execute(self.player_states)

        if not settle_details and self.pot > 0:
            # 異常系：誰もアクティブでない場合は返金
            self.refund_all()
            return [], 0

        self.status = "settled"
        Logger.info("Poker", f"Game settled in channel:{self.channel_id}")
        return settle_details, rake_amount

    async def process_npc_turns(self, view_callback=None) -> bool:
        """NPCの手番が続く限り、自動でアクションを実行する。アクションがあった場合はTrueを返す。"""
        any_npc_acted = False

        # 人間プレイヤーが全員フォールドしている場合はNPCの行動をスキップして即時ショウダウンへ
        active_humans = [
            p for p in self.player_states.values() if not p.is_npc and p.status != "folded"
        ]
        if not active_humans and self.status == "playing":
            self.phase = "showdown"
            while len(self.community_cards) < 5:
                card = self.deck.draw()
                if card:
                    self.community_cards.append(card)
            return any_npc_acted

        while True:
            current_p = self.get_current_player()
            if not current_p or self.phase == "showdown" or self.status != "playing":
                break

            p_state = self.player_states.get(current_p["id"])
            if not p_state or not p_state.is_npc:
                break

            # AIインスタンスを取得して決定
            ai = get_ai_instance(p_state)

            # MonsterAIの場合、リバーフェーズならイカサマ（手札入れ替え）を試行
            if p_state.ai_rank == "monster" and self.phase == "river":
                if hasattr(ai, "cheat_hand"):
                    ai.cheat_hand(self)

            action, amount = ai.decide_action(self)

            # UX向上のための待機（View側ではなくサービス側で一括管理）
            # テスト環境では高速化のためにスキップする
            if os.getenv("APP_ENV") != "test":
                await asyncio.sleep(1.5)

            try:
                success, msg = self.handle_action(p_state.user_id, action, amount)
            except PokerError as e:
                # NPCのエラーはログに記録し、ループを抜ける
                Logger.error("Poker", f"NPC Action failed after recovery: {e}")
                break

            any_npc_acted = True

            if view_callback:
                # View側に更新（メッセージ送信等）を通知
                await view_callback(p_state, action, amount, msg)

            if not success:
                # 依然として失敗する場合は予期せぬエラーのためループを抜ける
                break
        return any_npc_acted

    def _decide_table_blueprint(self, needed: int):
        """NPCの補充数に合わせて卓の構成案（設計図）を決定する"""
        if needed <= 0:
            return

        # ランクの抽選（Monster 5%, Legendary 25%, Rare 40%, Common 20%, Trash 10%）
        ranks = ["monster", "legendary", "rare", "common", "trash"]
        weights = [5, 25, 40, 20, 10]
        self.game_rank = random.choices(ranks, weights=weights)[0]

        # 構成案データの読み込み
        blueprint_path = os.path.join("data", "poker_blueprints.json")
        try:
            with open(blueprint_path, "r", encoding="utf-8") as f:
                all_blueprints = json.load(f)

            # 該当ランクかつ人数（needed）に合うリストを取得
            templates = all_blueprints.get(self.game_rank, {}).get(str(needed), [])
            if templates:
                # テンプレートの中からランダムに1つ選択
                chosen = random.choice(templates)
                # 形式を揃える: [{rank, personality}, ...]
                self.npc_blueprints = []
                c_ranks = chosen.get("ranks", [])
                c_pers = chosen.get("personalities", [])

                for i in range(needed):
                    rank = c_ranks[i] if i < len(c_ranks) else "common"
                    personality = c_pers[i] if i < len(c_pers) else None
                    self.npc_blueprints.append({"rank": rank, "personality": personality})

                Logger.info(
                    "Poker",
                    f"Table Blueprint Selected: '{chosen.get('name', 'Unknown')}' (Rank: {self.game_rank})",
                )
                return
        except Exception as e:
            Logger.error("Poker", f"Failed to load table blueprints: {e}")

        # 失敗時のフォールバック（全員そのランクにする）
        self.npc_blueprints = [{"rank": self.game_rank, "personality": None} for _ in range(needed)]
