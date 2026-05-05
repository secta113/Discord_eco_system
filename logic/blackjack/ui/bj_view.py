import asyncio
import io

import discord

from core.ui.view_base import BaseView
from core.utils.formatters import f_pts
from logic.blackjack.bj_canvas import BlackjackCanvas
from logic.blackjack.bj_deck import Deck
from logic.blackjack.bj_service import BlackjackService


class BlackjackBaseView(BaseView):
    """ブラックジャック関連の共通エラーハンドリングを備えた基底View"""

    pass


class BlackjackView(BlackjackBaseView):
    """
    ブラックジャックのUI。
    参加人数に応じて「ソロ風表示」と「マルチ風表示」を切り替える。
    """

    def __init__(self, session: BlackjackService, cleanup_callback=None, save_callback=None):
        super().__init__(timeout=None)  # セッション側で管理
        self.session = session
        self.cleanup_callback = cleanup_callback
        self.save_callback = save_callback
        self.canvas = BlackjackCanvas()
        # 画像キャッシュ: {cache_key: bytes}
        self._image_cache = {}
        # 送信済みアタッチメントの追跡: {filename: cache_key}
        self._last_sent_cache_keys = {}

    async def _update_display(self, interaction, message_text, is_game_end=False, is_first=False):
        # 現状の手番プレイヤーの状態を見てDouble Down/Splitボタンの有効/無効を判定
        current_p = self.session.get_current_player()
        if current_p and not is_game_end:
            player = self.session.player_states[current_p["id"]]
            hand = player.get_active_hand()

            double_btn = discord.utils.get(self.children, label="Double Down")
            if double_btn:
                double_btn.disabled = len(hand.cards) != 2 or hand.is_doubled

            split_btn = discord.utils.get(self.children, label="Split")
            if split_btn:
                can_split = (
                    len(hand.cards) == 2
                    and Deck.VALUES[hand.cards[0][1]] == Deck.VALUES[hand.cards[1][1]]
                    and len(player.hands) < 2
                )
                split_btn.disabled = not can_split

        # メッセージオブジェクト（アタッチメント確認用）を取得
        msg = (
            interaction.message
            if interaction.type == discord.InteractionType.component
            else self.message
        )
        current_attachments = msg.attachments if msg else None

        # Embedと画像の生成
        embeds, files = await self._build_game_embeds(
            message_text, is_game_end, attachments=current_attachments
        )

        if is_game_end:
            self.clear_items()
            self.stop()
            if self.cleanup_callback:
                self.cleanup_callback()

        await self._send_or_update(interaction, embeds, files, is_first=is_first)

    async def _get_cached_image_file(
        self, cache_key, hands_list, hide_first=False, filename="hand.png", attachments=None
    ):
        """キャッシュを確認し、なければ生成してFileオブジェクトまたは既存のAttachmentを返す"""
        # 1. すでに送信済みのアタッチメントがあり、今回のキャッシュキーと同じなら再利用
        if attachments and self._last_sent_cache_keys.get(filename) == cache_key:
            for attr in attachments:
                if attr.filename == filename:
                    from core.utils.logger import Logger

                    Logger.info("Blackjack", f"Reusing attachment: {filename} (cache hit)")
                    return attr

        # 2. メモリキャッシュの確認
        if cache_key in self._image_cache:
            buf = io.BytesIO(self._image_cache[cache_key])
            self._last_sent_cache_keys[filename] = cache_key
            return discord.File(buf, filename=filename)

        # 3. 新規生成 (別スレッドにオフロード)
        buf = await asyncio.to_thread(
            self.canvas.render_split_hands, hands_list, hide_first=hide_first
        )
        img_bytes = buf.getvalue()
        self._image_cache[cache_key] = img_bytes
        self._last_sent_cache_keys[filename] = cache_key

        buf.seek(0)
        return discord.File(buf, filename=filename)

    async def _build_game_embeds(self, message_text, is_game_end, attachments=None):
        """ディーラー、プレイヤーごとのEmbedと画像を生成する"""
        embeds = []
        files = []

        # 1. ディーラーのEmbed
        d_hand = self.session.dealer_hand
        d_score = Deck.get_score(d_hand) if is_game_end else "?"
        d_embed = discord.Embed(title=f"🕴️ ディーラー (計: {d_score})", color=0x34495E)

        # ディーラー画像キャッシュキー: 手札カードリスト + 公開状態
        d_cache_key = f"dealer_{hash(tuple(tuple(c) for c in d_hand))}_{is_game_end}"
        d_file = await self._get_cached_image_file(
            d_cache_key,
            [d_hand],
            hide_first=(not is_game_end),
            filename="dealer_hand.png",
            attachments=attachments,
        )
        d_embed.set_image(url="attachment://dealer_hand.png")

        if not is_game_end:
            d_embed.description = "1枚は伏せられています。"

        embeds.append(d_embed)
        files.append(d_file)

        # 2. 各プレイヤーのEmbed
        current_p = self.session.get_current_player()
        for p_info in self.session.players:
            uid = p_info["id"]
            player = self.session.player_states[uid]
            is_turn = not is_game_end and current_p and current_p["id"] == uid

            p_color = 0x2ECC71 if is_turn else 0x95A5A6
            p_embed = discord.Embed(title=f"👤 {p_info['name']}", color=p_color)

            # 複数手札（スプリット）対応
            hands_info = []
            hands_cards = []
            for h_idx, hand in enumerate(player.hands):
                hand_label = f"手札 {h_idx + 1}" if len(player.hands) > 1 else "手札"
                active_mark = "▶️ " if (is_turn and h_idx == player.active_hand_index) else "・ "

                status_str = f" [{hand.status.upper()}]" if hand.status != "playing" else ""

                score_str = f"計: **{hand.score}**"
                if hand.is_doubled:
                    score_str += " (Double)"

                hands_info.append(f"{active_mark}**{hand_label}**: {score_str}{status_str}")
                hands_cards.append(hand.cards)

            # プレイヤー画像キャッシュキー: UID + 全手札の構造化されたハッシュ
            hands_tuple = tuple(tuple(tuple(c) for c in h) for h in hands_cards)
            p_cache_key = f"p_{uid}_{hash(hands_tuple)}"
            p_filename = f"player_{uid}.png"
            p_file = await self._get_cached_image_file(
                p_cache_key, hands_cards, filename=p_filename, attachments=attachments
            )

            p_embed.set_image(url=f"attachment://{p_filename}")
            p_embed.description = "\n".join(hands_info)
            embeds.append(p_embed)
            files.append(p_file)

        # 最後のEmbedにメッセージテキストを追加
        target_embed = embeds[-1]
        target_embed.description = (target_embed.description or "") + f"\n\n📢 {message_text}"
        target_embed.set_footer(text=f"デッキ残数: {len(self.session.deck.cards)}枚")

        return embeds, files

    async def _send_or_update(self, interaction, embeds, files, is_first=False):
        """メッセージ送信の共通ロジック"""
        if is_first:
            if interaction.response.is_done():
                self.message = await interaction.followup.send(
                    embeds=embeds, files=files, view=self
                )
            else:
                await interaction.response.send_message(embeds=embeds, files=files, view=self)
                self.message = await interaction.original_response()
            return

        if interaction.response.is_done():
            self.message = await interaction.edit_original_response(
                embeds=embeds, attachments=files, view=self
            )
        elif interaction.type == discord.InteractionType.component:
            # edit_message も同様に attachments を常に渡して更新
            await interaction.response.edit_message(embeds=embeds, attachments=files, view=self)
        else:
            await interaction.response.send_message(embeds=embeds, files=files, view=self)
            self.message = await interaction.original_response()

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        msg, is_turn_end = self.session.current_player_action(interaction.user.id, "hit")

        if is_turn_end:
            await self._next_turn(interaction, msg)
        else:
            if self.save_callback:
                self.save_callback()
            await self._update_display(
                interaction, f"{interaction.user.mention} がHitしました。\n{msg}"
            )

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.secondary)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        msg, is_turn_end = self.session.current_player_action(interaction.user.id, "stand")
        await self._next_turn(interaction, msg)

    @discord.ui.button(label="Double Down", style=discord.ButtonStyle.success)
    async def double_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        msg, is_turn_end = self.session.current_player_action(interaction.user.id, "double")

        if is_turn_end:
            await self._next_turn(interaction, msg)
        else:
            if self.save_callback:
                self.save_callback()
            await self._update_display(
                interaction, f"{interaction.user.mention} がアクションしました。\n{msg}"
            )

    @discord.ui.button(label="Split", style=discord.ButtonStyle.success)
    async def split(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        msg, is_turn_end = self.session.current_player_action(interaction.user.id, "split")

        if is_turn_end:
            await self._next_turn(interaction, msg)
        else:
            if self.save_callback:
                self.save_callback()
            await self._update_display(
                interaction, f"{interaction.user.mention} がアクションしました。\n{msg}"
            )

    async def _next_turn(self, interaction, last_action_msg):
        """ターンを進める処理"""
        has_next = self.session.advance_turn_if_needed()

        if has_next:
            if self.save_callback:
                self.save_callback()
            next_p = self.session.get_current_player()
            await self._update_display(
                interaction, f"{last_action_msg}\n次は {next_p['mention']} の番です。"
            )
        else:
            # 全員終了 -> ディーラーターン演出
            self.session.is_dealer_turn_executed = True

            # 手を隠さず表示するため一度更新
            await self._update_display(interaction, f"{last_action_msg}\nディーラーの番です。")
            await asyncio.sleep(1.0)

            # 1枚ずつ引く演出
            while self.session.should_dealer_draw():
                card_str = self.session.dealer_draw_step()
                await self._update_display(
                    interaction, f"ディーラーがカードを引いています: {card_str}"
                )
                await asyncio.sleep(1.2)

            # 最終決着
            results = self.session.settle_all()

            # 結果表示用テキスト作成
            d_score = Deck.get_score(self.session.dealer_hand)
            res_text = f"ディーラーのスコア: **{d_score}**\n\n"
            for r in results:
                res_text += f"**{r['name']}** (計: {f_pts(r['total_payout'])}):\n"
                for hr in r["hands"]:
                    res_text += f"> {hr['result']}\n"
                res_text += "\n"

            await self._update_display(
                interaction,
                f"🏆 **ゲーム終了** 🏆\n{res_text}",
                is_game_end=True,
            )

    @property
    def message(self):
        return self._message if hasattr(self, "_message") else None

    @message.setter
    def message(self, value):
        self._message = value
