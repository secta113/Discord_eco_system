import asyncio
import io
import logging
from typing import Optional

import discord
from discord import ui

from core.ui.view_base import BaseView
from core.utils.formatters import f_bold_pts, f_commas, f_pts
from core.utils.logger import Logger
from logic.poker.pk_canvas import PokerCanvas
from logic.poker.pk_deck import PokerDeck
from logic.poker.pk_exceptions import PokerError, PokerTurnError
from logic.poker.pk_formatter import PokerFormatter
from logic.poker.pk_service import TexasPokerService


class PokerBaseView(BaseView):
    """ポーカー関連の共通エラーハンドリングを備えた基底View"""

    pass


class RaiseModal(ui.Modal, title="レイズ額の入力"):
    """レイズ額を入力するためのモーダル"""

    amount_input = ui.TextInput(
        label="合計ベット額を入力してください",
        placeholder="例: 100",
        min_length=1,
        max_length=10,
    )

    def __init__(self, view, interaction: discord.Interaction):
        super().__init__()
        self.view = view
        self.original_interaction = interaction
        # デフォルト値を現在のミニマムレイズ額に設定
        min_raise = self.view.session.current_max_bet + self.view.session.big_blind
        self.amount_input.default = str(min_raise)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.amount_input.value)
            if amount <= 0:
                raise ValueError
        except ValueError:
            return await interaction.response.send_message(
                "正の数値を入力してください。", ephemeral=True
            )

        await self.view._handle_action(interaction, "raise", amount=amount)


class PokerView(PokerBaseView):
    """
    v1.1 テキサス・ホールデムのUI（チェック・数値レイズ・オールイン対応）。
    """

    def __init__(self, session: TexasPokerService, cleanup_callback=None, save_callback=None):
        super().__init__(timeout=None)
        self.session = session
        self.cleanup_callback = cleanup_callback
        self.save_callback = save_callback
        self.canvas = PokerCanvas()

        # 画像キャッシュ用
        self._cached_table_img: Optional[bytes] = None
        self._last_community_cards: list = []

    async def update_display(
        self,
        interaction: discord.Interaction,
        message_text: str,
        is_game_end: bool = False,
        is_first: bool = False,
    ):
        """現在のゲーム状態を反映したEmbedを表示。"""
        # ボタンの有効/無効を更新
        self._update_buttons(is_game_end)
        embeds = self._create_embeds(message_text, is_game_end)

        # テーブル画像の生成またはキャッシュ利用
        file, is_changed = await self._get_table_file(force=is_first)
        # 1番目のEmbed (ボード専用) に画像をセット
        embeds[0].set_image(url="attachment://table.png")

        if is_first:
            # 初回表示は必ずファイルが必要
            if not file:
                # 万が一取得できなかった場合のフォールバック（空画像生成）
                img_buf = await asyncio.to_thread(self.canvas.render_table, [], 0, "pre_flop")
                file = discord.File(img_buf, filename="table.png")

            if interaction.response.is_done():
                self.message = await interaction.followup.send(embeds=embeds, file=file, view=self)
            else:
                await interaction.response.send_message(embeds=embeds, file=file, view=self)
                self.message = await interaction.original_response()
        else:
            # 更新 (同じメッセージを編集)
            try:
                # 画像に変更がある場合のみ attachments を含める
                edit_kwargs = {"embeds": embeds, "view": self}
                if is_changed:
                    edit_kwargs["attachments"] = [file]

                if not interaction.response.is_done():
                    await interaction.response.edit_message(**edit_kwargs)
                elif self.message:
                    await self.message.edit(**edit_kwargs)
                else:
                    # メッセージが見つからない場合は新規投稿（ファイル必須）
                    if not file:
                        file, _ = await self._get_table_file(force=True)
                    self.message = await interaction.channel.send(
                        embeds=embeds, file=file, view=self
                    )
            except (discord.HTTPException, discord.InteractionResponded, discord.NotFound):
                # 失敗した場合は新規メッセージとして再送
                try:
                    if not file:
                        file, _ = await self._get_table_file(force=True)
                    self.message = await interaction.channel.send(
                        embeds=embeds, file=file, view=self
                    )
                except discord.HTTPException:
                    pass

    def _create_embeds(self, message_text: str, is_game_end: bool) -> list[discord.Embed]:
        """ボード用とステータス用の2つのEmbedを生成する。"""
        phase_names = {
            "pre_flop": "プリフロップ",
            "flop": "フロップ",
            "turn": "ターン",
            "river": "リバー",
            "showdown": "ショウダウン",
        }
        phase_label = phase_names.get(self.session.phase, self.session.phase)
        title = f"♣️ テキサス・ホールデム ({phase_label})"
        color = 0x1F8B4C  # Dark Green

        # 1. ボード用Embed (最上部に固定)
        board_embed = discord.Embed(title=title, color=color)

        # 2. ステータス用Embed (画像の下に配置)
        status_embed = discord.Embed(color=color)

        # アクションログ
        status_embed.add_field(name="📢 直近のアクション", value=message_text, inline=False)

        # 基本情報
        status_embed.add_field(name="📍 フェーズ", value=f"**{phase_label}**", inline=True)
        status_embed.add_field(name="💰 総ポット", value=f_bold_pts(self.session.pot), inline=True)
        status_embed.add_field(
            name="📈 最高ベット", value=f_pts(self.session.current_max_bet), inline=True
        )

        # プレイヤー一覧
        players_str = ""
        current_p = self.session.get_current_player()
        num_players = len(self.session.players)

        # ポジション計算
        if num_players == 2:
            sb_idx, bb_idx = (
                self.session.button_index,
                (self.session.button_index + 1) % num_players,
            )
        else:
            sb_idx, bb_idx = (
                (self.session.button_index + 1) % num_players,
                (self.session.button_index + 2) % num_players,
            )

        for i, p in enumerate(self.session.players):
            uid = p["id"]
            state = self.session.player_states[uid]
            prefix = "▶️ " if (not is_game_end and current_p and current_p["id"] == uid) else "・ "

            pos_label = ""
            if i == self.session.button_index:
                pos_label = " 🔵D"
            elif i == sb_idx:
                pos_label = " 🔸SB"
            elif i == bb_idx:
                pos_label = " 🔸BB"

            p_status = ""
            if state.status == "folded":
                p_status = " ❌ Folded"
            elif state.is_all_in:
                p_status = " 🔥 All-in"

            hand_str = ""
            if is_game_end and state.status != "folded":
                h1 = PokerDeck.format_card(state.hole_cards[0])
                h2 = PokerDeck.format_card(state.hole_cards[1])
                hand_str = f" `{h1} {h2}`"

            players_str += (
                f"{prefix}**{p['name']}**{pos_label}{p_status}\n"
                f"　 💰 **Stack**: {f_pts(state.stack)} | 🎲 **Bet**: {f_pts(state.current_bet)}{hand_str}\n"
            )

        status_embed.add_field(name=f"👥 参加者 ({num_players}人)", value=players_str, inline=False)
        status_embed.set_footer(text="「手札を確認」ボタンで自分のホールカードを確認できます。")

        return [board_embed, status_embed]

    def _update_buttons(self, is_game_end: bool):
        if is_game_end:
            for child in self.children:
                child.disabled = True
            if self.cleanup_callback:
                self.cleanup_callback()
            return

        current_p = self.session.get_current_player()
        current_id = current_p["id"] if current_p else None
        p_state = self.session.player_states.get(current_id) if current_id else None

        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.custom_id == "show_hand":
                    child.disabled = False
                    continue

                # 手番のプレイヤー以外は無効化
                child.disabled = current_id is None

                # Check / Call のラベル切り替え
                if child.custom_id == "call_btn":
                    if p_state and p_state.current_bet >= self.session.current_max_bet:
                        child.label = "Check"
                        child.style = discord.ButtonStyle.primary
                    else:
                        child.label = "Call"
                        child.style = discord.ButtonStyle.success

    @discord.ui.button(
        label="手札を確認", style=discord.ButtonStyle.secondary, custom_id="show_hand"
    )
    async def show_hand(self, interaction: discord.Interaction, button: discord.ui.Button):
        # カード確認は ephemeral で即座に defer する
        for attempt in range(3):
            try:
                await interaction.response.defer(ephemeral=True)
                break
            except discord.HTTPException as e:
                Logger.warning(
                    "Poker", f"[Poker] show_hand defer failed (attempt {attempt + 1}): {e}"
                )
                if attempt == 2:
                    raise PokerError(
                        "Discord APIが応答しませんでした。少し待ってから再度お試しください。"
                    )
                await asyncio.sleep(1.0)

        uid = interaction.user.id
        player = self.session.player_states.get(uid)
        if not player:
            raise PokerError("ゲームに参加していません。")
        cards = player.hole_cards
        if not cards:
            raise PokerError("カードが配られていません。")

        # 手札画像の生成 (別スレッドにオフロード)
        img_buf = await asyncio.to_thread(self.canvas.render_hand, cards)
        file = discord.File(img_buf, filename="hand.png")

        # Embedの作成 (手札用)
        embed = discord.Embed(
            title="🃏 あなたの手札",
            description=f"現在の持ち点 (Stack): {f_bold_pts(player.stack)}",
            color=discord.Color.blue(),
        )
        embed.set_image(url="attachment://hand.png")

        await interaction.followup.send(embed=embed, file=file, ephemeral=True)

    @discord.ui.button(
        label="Check / Call", style=discord.ButtonStyle.primary, custom_id="call_btn"
    )
    async def call(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = interaction.user.id
        p_state = self.session.player_states.get(uid)
        if not p_state:
            raise PokerError("ゲームに参加していません。")
        # 現在のベット額が並んでいれば check、足りなければ call
        action = "check" if p_state.current_bet >= self.session.current_max_bet else "call"
        await self._handle_action(interaction, action)

    @discord.ui.button(label="Raise", style=discord.ButtonStyle.secondary, custom_id="raise_btn")
    async def raise_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Service側でのチェックを事前に行う（Modal表示の無駄を防ぐため）
        current_p = self.session.get_current_player()
        if not current_p or interaction.user.id != current_p["id"]:
            raise PokerTurnError()

        await interaction.response.send_modal(RaiseModal(self, interaction))

    @discord.ui.button(label="All-In", style=discord.ButtonStyle.primary, custom_id="allin_btn")
    async def all_in(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_action(interaction, "all_in")

    @discord.ui.button(label="Fold", style=discord.ButtonStyle.danger, custom_id="fold_btn")
    async def fold(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in self.session.player_states:
            return await interaction.response.send_message(
                "ゲームに参加していません。", ephemeral=True
            )
        await self._handle_action(interaction, "fold")

    async def _handle_action(self, interaction: discord.Interaction, action: str, amount: int = 0):
        # アクション開始時にレスポンスを確保
        if not interaction.response.is_done():
            for attempt in range(3):
                try:
                    await interaction.response.defer()
                    break
                except discord.HTTPException as e:
                    Logger.warning("Poker", f"[Poker] defer failed (attempt {attempt + 1}): {e}")
                    if attempt == 2:
                        raise PokerError(
                            "Discord側のサーバーが混雑しているため、アクションが処理できませんでした。もう一度お試しください。"
                        )
                    await asyncio.sleep(1.0)

        Logger.info(
            "Poker",
            f"[Poker] Action: {action} by {interaction.user.display_name} (amount={amount})",
        )

        # 例外が発生した場合は PokerBaseView.on_error がキャッチする
        _, msg = self.session.handle_action(interaction.user.id, action, amount=amount)

        if self.save_callback:
            self.save_callback()

        # ゲーム終了判定（人間が最後のアクションでショウダウンになった場合）
        if self.session.phase == "showdown":
            await self._finish_game(interaction)
            return

        # 手番が進んだことを表示
        next_p = self.session.get_current_player()
        next_mention = f"\n<@{next_p['id']}> の番です。" if next_p else ""

        display_action = self._format_action_name(action, amount)
        await self.update_display(
            interaction,
            f"{interaction.user.mention} が **{display_action}** しました。\n{msg}{next_mention}",
            is_game_end=False,
        )

        # NPCの手番があれば自動実行
        npc_acted = await self.session.process_npc_turns(view_callback=self._npc_action_callback)

        # 全てのNPC手番が終わった後の再描画（ショウダウン移行の可能性あり）
        if self.session.phase == "showdown":
            await self._finish_game(interaction)
        else:
            # 次の人間プレイヤーの手番を促す
            next_p = self.session.get_current_player()
            if next_p:
                if npc_acted:
                    text = f"NPCのアクションが完了しました。<@{next_p['id']}> の番です。"
                else:
                    text = f"<@{next_p['id']}> の番です。"

                # ターン進行のために新メッセージを投げる
                await self.update_display(interaction, text, is_game_end=False)

    async def _npc_action_callback(self, npc_state, action, amount, msg):
        """NPCのアクションごとにUIを更新する"""
        self._update_buttons(False)
        display_action = self._format_action_name(action, amount)
        text = f"**{npc_state.name}** が **{display_action}** しました。\n{msg}"

        # 2段Embedを生成
        embeds = self._create_embeds(text, False)

        # テーブル画像の生成またはキャッシュ利用
        file, is_changed = await self._get_table_file()
        embeds[0].set_image(url="attachment://table.png")

        # NPCの手番ごとにメッセージを更新
        if self.message:
            try:
                edit_kwargs = {"embeds": embeds, "view": self}
                if is_changed:
                    edit_kwargs["attachments"] = [file]
                await self.message.edit(**edit_kwargs)
            except discord.HTTPException:
                pass

    async def _get_table_file(self, force=False) -> tuple[Optional[discord.File], bool]:
        """キャッシュを確認し、必要に応じてテーブル画像を生成して (file, is_changed) を返す"""
        current_cards = self.session.community_cards

        # カードが一致していれば None, False を返す（空の状態も含めてキャッシュ可能にする）
        if (
            not force
            and self._cached_table_img is not None
            and self._last_community_cards == current_cards
        ):
            return None, False

        # キャッシュがない、またはカードが変わった場合は再描画 (別スレッドにオフロード)
        img_buf = await asyncio.to_thread(
            self.canvas.render_table, current_cards, self.session.pot, self.session.phase
        )
        self._cached_table_img = img_buf.getvalue()
        self._last_community_cards = list(current_cards)  # コピーを保持
        img_buf.seek(0)
        return discord.File(img_buf, filename="table.png"), True

    def _format_action_name(self, action, amount):
        if action == "check":
            return "Check"
        if action == "call":
            return "Call"
        if action == "raise":
            return f"Raise ({f_pts(amount)})"
        if action == "all_in":
            return "All-In"
        if action == "fold":
            return "Fold"
        return action

    async def _finish_game(self, interaction: discord.Interaction):
        results, rake_amount = self.session.settle_game()
        res_text = "🏆 **結果発表** 🏆\n"
        for r in results:
            profit = r.get("profit", 0)
            line = f"**{r['name']}**: {r['hand']} ({f_pts(profit, signed=True)})"

            jp_payout = r.get("jp_payout", 0)
            if jp_payout > 0:
                line += f" 🎰 (内 JP: +{f_pts(jp_payout)})"

            res_text += line + "\n"

        if rake_amount > 0:
            res_text += (
                f"\n*※ポットから手数料(Rake 5%)として {f_pts(rake_amount)} が徴収されました。*"
            )

        await self.update_display(interaction, res_text, is_game_end=True)

    @property
    def message(self):
        # 既存のメッセージを特定する（update_displayで使われるinteraction.original_response等でも良い）
        # Viewが保持しているはずの message 属性。discord.py の View には message 属性はない場合があるが、
        # starter.py 等でセットされている前提、もしくは interaction 経由で取得。
        return self._message if hasattr(self, "_message") else None

    @message.setter
    def message(self, value):
        self._message = value
