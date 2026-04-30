from typing import TYPE_CHECKING, Any, Callable, List, Optional

import discord

from core.utils.time_utils import get_jst_today

from .dob_common import DobumonBaseView, DobumonSelect, MenuSelect
from .dob_formatter import DobumonFormatter

if TYPE_CHECKING:
    from logic.dobumon.core.dob_models import Dobumon


class TrainingView(DobumonBaseView):
    """
    トレーニング対象とメニューを段階的に選択するためのView。
    """

    def __init__(
        self,
        user: discord.User,
        dobumons: List["Dobumon"],
        callback_func: Callable,
        cost_calc_func: Optional[Callable] = None,
        timeout: float = 120.0,
        initial_dobumon_id: Optional[str] = None,
    ):
        super().__init__(user=user, timeout=timeout)
        self.dobumons = dobumons
        self.callback_func = callback_func
        self.cost_calc_func = cost_calc_func
        self.selected_dobumon_id: Optional[str] = initial_dobumon_id
        self.selected_menu: Optional[str] = None

        # セレクトメニューを追加
        self.dobumon_select = DobumonSelect(dobumons, "トレーニングする怒武者を選択...")
        self.menu_select = MenuSelect()
        self.add_item(self.dobumon_select)
        self.add_item(self.menu_select)

    def create_initial_embed(self) -> discord.Embed:
        """初期表示用のEmbedを作成する"""
        dobu = None
        if self.selected_dobumon_id:
            dobu = next(
                (d for d in self.dobumons if d.dobumon_id == self.selected_dobumon_id), None
            )

        title = "🏋️ トレーニング・ウィザード"
        description = "対象の怒武者と練習メニューを選んでください。\n両方選択すると「トレーニング開始」ボタンが有効になります。"
        color = 0x3498DB

        if dobu and self.cost_calc_func:
            cost = self.cost_calc_func(dobu)
            description += f"\n\n💰 **必要費用**: `{cost:,}` pts"
            if dobu.affection >= 100:
                description += " (絆による割引適用中)"

        # 初期選択がある場合はセレクトメニューのデフォルトを更新
        if self.selected_dobumon_id:
            for option in self.dobumon_select.options:
                option.default = option.value == self.selected_dobumon_id

        return discord.Embed(title=title, description=description, color=color)

    async def update_message(self, interaction: discord.Interaction):
        """選択状態に合わせてメッセージを更新する"""
        # 選択個体情報の取得
        dobu = None
        if self.selected_dobumon_id:
            dobu = next(
                (d for d in self.dobumons if d.dobumon_id == self.selected_dobumon_id), None
            )

        # 今日の日付を取得
        today_str = get_jst_today()
        is_overworked = dobu and dobu.last_train_date == today_str and dobu.today_train_count >= 5

        # オーバーワーク時のメニュー初期選択（利便性向上のため）
        if is_overworked and self.selected_menu is None:
            self.selected_menu = "massage"

        # セレクトメニューの状態を更新
        for option in self.dobumon_select.options:
            option.default = option.value == self.selected_dobumon_id

        for option in self.menu_select.options:
            option.default = option.value == self.selected_menu

        title = "🏋️ トレーニング・ウィザード"
        description = "対象の怒武者と練習メニューを選んでください。\n両方選択すると「トレーニング開始」ボタンが有効になります。"
        footer_text = ""
        color = 0x3498DB

        # 費用の計算と表示
        if dobu and self.cost_calc_func:
            cost = self.cost_calc_func(dobu)
            description += f"\n\n💰 **必要費用**: `{cost:,}` pts"
            if dobu.affection >= 100:
                description += " (絆による割引適用中)"

        # オーバーワーク警告の追加
        if is_overworked:
            # 休息メニュー以外が選ばれている場合に警告を強調
            warning = "\n\n⚠️ **オーバーワーク警告**\nこの怒武者は既に5回以上の特訓を行っています。これ以上の特訓は寿命を縮めるリスクがあります。\n（※「マッサージ・お昼寝」は例外であり、体力回復とペナルティ回避が可能です）"
            description += warning
            color = 0xE67E22  # オレンジ

        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
        )

        # 実行ボタンの状態管理
        self.start_button.disabled = not (self.selected_dobumon_id and self.selected_menu)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="トレーニング開始", style=discord.ButtonStyle.success, disabled=True)
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not self.selected_dobumon_id or not self.selected_menu:
            return await interaction.response.send_message("⚠️ 選択が不十分です。", ephemeral=True)

        # 二重送信防止のためにUIを無効化
        button.disabled = True
        button.label = "実行中..."
        self.dobumon_select.disabled = True
        self.menu_select.disabled = True
        await interaction.response.edit_message(view=self)

        self.stop()
        # 実行
        await self.callback_func(interaction, self.selected_dobumon_id, self.selected_menu)


class TrainingResultView(DobumonBaseView):
    """
    トレーニング完了後に表示するアクションView。
    """

    def __init__(
        self,
        user: discord.User,
        manager: Any,
        service: Any,
        last_dobumon_id: str,
        timeout: float = 60.0,
    ):
        super().__init__(user=user, timeout=timeout)
        self.manager = manager
        self.service = service
        self.last_dobumon_id = last_dobumon_id

    @discord.ui.button(label="続けてトレーニングする", style=discord.ButtonStyle.primary)
    async def continue_training(self, interaction: discord.Interaction, button: discord.ui.Button):

        # 二重操作防止のため、現在のViewの全アイテムを無効化して更新
        for item in self.children:
            if isinstance(item, (discord.ui.Button, discord.ui.Select)):
                item.disabled = True
        await interaction.response.edit_message(view=self)

        # 最新の怒武者リストを取得
        dobumons = self.manager.get_user_dobumons(self.user.id, only_alive=True)
        if not dobumons:
            return await interaction.followup.send(
                "トレーニング可能な怒武者を所持していません。", ephemeral=True
            )

        # 新しい TrainingView を作成
        from logic.dobumon.training import TrainingEngine

        view = TrainingView(
            self.user,
            dobumons,
            self.service.execute_training,
            TrainingEngine.calculate_training_cost,
            initial_dobumon_id=self.last_dobumon_id,
        )
        embed = view.create_initial_embed()
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        self.stop()

    @discord.ui.button(label="ステータスを表示", style=discord.ButtonStyle.secondary)
    async def show_status(self, interaction: discord.Interaction, button: discord.ui.Button):

        dobu = self.manager.get_dobumon(self.last_dobumon_id)
        if not dobu:
            return await interaction.response.send_message(
                "怒武者が見つかりませんでした。", ephemeral=True
            )

        embed = DobumonFormatter.format_status_embed(dobu)
        embed.title = f"📊 {dobu.name} の現在の能力"
        await interaction.response.send_message(embed=embed, ephemeral=True)
