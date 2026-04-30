from typing import TYPE_CHECKING, Callable, List

import discord

from .dob_common import DobumonBaseView, DobumonSelect
from .dob_formatter import DobumonFormatter

if TYPE_CHECKING:
    from logic.dobumon.core.dob_models import Dobumon


class DobumonSellView(DobumonBaseView):
    """
    怒武者を売却するためのウィザード。
    """

    def __init__(
        self,
        user: discord.User,
        dobumons: List["Dobumon"],
        sell_callback: Callable,
        price_calculator: Callable,
    ):
        super().__init__(user=user, timeout=60)
        self.dobumons = dobumons
        self.sell_callback = sell_callback
        self.price_calculator = price_calculator
        self.selected_dobumon_id = None

        # セレクトメニューの追加
        self.select_menu = DobumonSelect(
            dobumons, placeholder="売却する怒武者を選択してください..."
        )
        self.add_item(self.select_menu)

        # 売却ボタン（初期は無効）
        self.sell_button = discord.ui.Button(
            label="売却する",
            style=discord.ButtonStyle.danger,
            custom_id="sell_confirm",
            disabled=True,
        )
        self.sell_button.callback = self._on_sell_click
        self.add_item(self.sell_button)

        # キャンセルボタン
        self.cancel_button = discord.ui.Button(
            label="キャンセル",
            style=discord.ButtonStyle.secondary,
            custom_id="sell_cancel",
        )
        self.cancel_button.callback = self._on_cancel_click
        self.add_item(self.cancel_button)

    async def update_message(self, interaction: discord.Interaction):
        """セレクトメニュー選択時に表示を更新"""
        dobu = next((d for d in self.dobumons if d.dobumon_id == self.selected_dobumon_id), None)
        if not dobu:
            return

        price = self.price_calculator(dobu)

        # ドロップダウンの選択状態を維持
        for option in self.select_menu.options:
            option.default = option.value == self.selected_dobumon_id

        # ステータス表示を /dobumon status と同じ形式にする
        embed = DobumonFormatter.format_status_embed(dobu, is_owner=True)
        embed.title = "💰 売却の確認"

        description = f"本当に **{dobu.name}** を売却しますか？\nこの操作は取り消せません。\n\n"
        description += f"💵 **売却提示価格: {price:,} pts**\n"

        # 禁忌深度の警告（あれば）
        forbidden_depth = dobu.genetics.get("forbidden_depth", 0)
        if forbidden_depth > 0:
            description += f"⚠️ **減額警告**: 禁忌深度 {forbidden_depth} により、売却額が **{forbidden_depth * 10}%** 減額されています。\n"

        description += "\n" + embed.description
        embed.description = description

        self.sell_button.disabled = False
        await interaction.response.edit_message(embed=embed, view=self)

    async def _on_sell_click(self, interaction: discord.Interaction):
        if not self.selected_dobumon_id:
            return

        # UIを無効化して連打防止
        for item in self.children:
            item.disabled = True

        # メッセージを更新（ボタン無効化状態を表示）
        await interaction.response.edit_message(view=self)

        # コールバック実行
        await self.sell_callback(interaction, self.selected_dobumon_id)
        self.stop()

    async def _on_cancel_click(self, interaction: discord.Interaction):
        """キャンセルボタン押下時の処理"""
        embed = discord.Embed(
            title="💰 売却ウィザード",
            description="売却をキャンセルしました。",
            color=0x95A5A6,
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()
