import discord
from discord import ui

from core.ui.view_base import BaseView, JoinView


class MatchJoinView(JoinView):
    """Match専用の参加View。ホスト専用の「結果報告」ボタンを持つ"""

    def __init__(self, channel_id, manager):
        super().__init__(channel_id, manager, show_start=False)

        cancel_item = None
        report_item = None
        for item in self.children:
            if getattr(item, "label", "") == "🛑 キャンセル":
                cancel_item = item
            elif getattr(item, "label", "") == "🏁 結果報告":
                report_item = item

        if cancel_item and report_item:
            self.remove_item(cancel_item)
            self.remove_item(report_item)
            self.add_item(report_item)
            self.add_item(cancel_item)

    @ui.button(label="🏁 結果報告", style=discord.ButtonStyle.primary)
    async def report_button(self, interaction: discord.Interaction, button: ui.Button):
        session = self.manager.get_session(self.channel_id)
        if not session or getattr(session, "game_type", "") != "match":
            return await interaction.response.send_message(
                "⚠️ 有効なゲームセッションがありません。", ephemeral=True
            )

        if session.host_id != interaction.user.id:
            return await interaction.response.send_message(
                "❌ ホストのみが結果報告できます。", ephemeral=True
            )

        if len(session.players) < 2:
            session.cancel()
            self.manager.end_session(self.channel_id)
            for child in self.children:
                child.disabled = True

            embed = discord.Embed(
                title="⚔️ 外部マッチ 対戦不成立",
                description="参加者が2名に満たないため、自動キャンセル（全額返金）されました。",
                color=0x95A5A6,
            )
            return await interaction.response.edit_message(embed=embed, view=self)

        view = MatchResultView(
            session, self.manager, original_message=interaction.message, original_view=self
        )
        await interaction.response.send_message(
            "👇 勝者を選択してください：", view=view, ephemeral=True
        )


class MatchResultSelect(ui.Select):
    """ホストが勝者を選択するドロップダウンUI"""

    def __init__(self, session, manager):
        self.session = session
        self.manager = manager
        options = []
        for p in session.players:
            options.append(discord.SelectOption(label=p["name"], value=str(p["id"])))
        if not options:
            options.append(discord.SelectOption(label="参加者なし", value="0"))

        super().__init__(
            placeholder="勝者を選択してください...",
            min_values=1,
            max_values=1,
            options=options[:25],
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        winner_id = int(self.values[0])
        if winner_id == 0:
            return await interaction.followup.send("勝者が無効です", ephemeral=True)

        payout = self.session.settle([winner_id])
        self.manager.end_session(self.session.channel_id)

        for item in self.view.children:
            item.disabled = True
        await interaction.edit_original_response(
            content="✅ 清算が完了し、全体へアナウンスしました。", view=self.view
        )

        if hasattr(self.view, "original_view") and hasattr(self.view, "original_message"):
            for child in self.view.original_view.children:
                child.disabled = True
            try:
                await self.view.original_message.edit(view=self.view.original_view)
            except Exception:
                pass

        winner_member = interaction.guild.get_member(winner_id) if interaction.guild else None
        winner_mention = winner_member.mention if winner_member else f"<@{winner_id}>"
        await interaction.channel.send(
            f"🏆 【マッチ結果】 勝者: {winner_mention} (配当: {payout} pts)"
        )


class MatchResultView(BaseView):
    def __init__(self, session, manager, original_message=None, original_view=None):
        super().__init__(timeout=300)
        self.original_message = original_message
        self.original_view = original_view
        self.add_item(MatchResultSelect(session, manager))
