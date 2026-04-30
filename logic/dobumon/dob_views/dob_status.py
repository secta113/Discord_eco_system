from typing import TYPE_CHECKING, List

import discord

from .dob_common import DobumonBaseView
from .dob_formatter import DobumonFormatter

if TYPE_CHECKING:
    from logic.dobumon.core.dob_models import Dobumon


class StatusSelectionView(DobumonBaseView):
    """
    所持している全怒武者の一覧を表示し、選択した個体の詳細ステータスを表示するView。
    """

    def __init__(self, user: discord.User, dobumons: List["Dobumon"]):
        super().__init__(user=user, timeout=120)
        self.dobumons = dobumons

        # セレクトメニューの追加
        self.add_dobumon_select()

    def add_dobumon_select(self):
        options = []
        for dobu in self.dobumons:
            # 属性アイコン
            attr_emoji = {"fire": "🔥", "water": "💧", "grass": "🌿"}.get(dobu.attribute, "⚔️")
            gender_icon = "♂️" if dobu.gender == "M" else "♀️"

            label = f"{dobu.name} ({gender_icon})"
            description = (
                f"第 {dobu.generation} 世代 | {dobu.attribute.upper()} | {dobu.life_stage}"
            )

            options.append(
                discord.SelectOption(
                    label=label, value=dobu.dobumon_id, description=description, emoji=attr_emoji
                )
            )

        select = discord.ui.Select(
            placeholder="詳細を確認する怒武者を選択...", options=options, custom_id="status_select"
        )
        select.callback = self.on_select
        self.add_item(select)

    async def on_select(self, interaction: discord.Interaction):

        selected_id = interaction.data["values"][0]
        dobu = next((d for d in self.dobumons if d.dobumon_id == selected_id), None)

        if not dobu:
            await interaction.response.send_message(
                "対象の怒武者が見つかりませんでした。", ephemeral=True
            )
            return

        # 詳細Embedの生成
        embed = DobumonFormatter.format_status_embed(dobu, is_owner=True)
        embed.set_footer(text="セレクトメニューから他の個体も確認できます。")

        # 元のメッセージ（一覧＋メニュー）を詳細Embedで更新
        await interaction.response.edit_message(embed=embed, view=self)

    @staticmethod
    def create_summary_embed(dobumons: List["Dobumon"]) -> discord.Embed:
        """所持個体の一覧サマリーEmbedを作成します。"""
        embed = discord.Embed(
            title="〓 怒武者 所持一覧 〓",
            description=f"現在は **{len(dobumons)}** 体の怒武者を所持しています。",
            color=0x34495E,
        )

        for dobu in dobumons:
            attr_emoji = {"fire": "🔥", "water": "💧", "grass": "🌿"}.get(dobu.attribute, "⚔️")
            gender_icon = "♂️" if dobu.gender == "M" else "♀️"

            # 簡潔なステータス行
            ratio = int((dobu.lifespan / dobu.max_lifespan) * 100) if dobu.max_lifespan > 0 else 0
            # 進行バー（短縮版）
            bar_len = 5
            filled = int(math.ceil((ratio / 100) * bar_len)) if ratio > 0 else 0
            bar = "★" * filled + "☆" * (bar_len - filled)

            value = (
                f"属性: {attr_emoji} | 世代: {dobu.generation}\n"
                f"寿命: {bar} ({ratio}%)\n"
                f"状態: {dobu.life_stage}"
            )
            if not dobu.is_alive:
                value += " (💀 死亡)"

            embed.add_field(name=f"{gender_icon} **{dobu.name}**", value=value, inline=True)

        embed.set_footer(text="下のメニューから詳細なステータスを確認できます。")
        return embed


# 必要な math import を追加
import math
