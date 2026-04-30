from typing import TYPE_CHECKING, List

import discord

if TYPE_CHECKING:
    from logic.dobumon.core.dob_models import Dobumon


class DobumonSelect(discord.ui.Select):
    """
    ドブモンを選択するためのセレクトメニュー。
    """

    def __init__(self, dobumons: List["Dobumon"], placeholder: str = "怒武者を選択..."):
        options = []
        for d in dobumons:
            options.append(
                discord.SelectOption(
                    label=d.name,
                    value=d.dobumon_id,
                    description=f"HP:{int(d.health or d.hp)}/{int(d.hp)} ATK:{int(d.atk)} DEF:{int(d.defense)} SPD:{int(d.spd)}",
                )
            )
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_dobumon_id = self.values[0]
        if hasattr(self.view, "update_message"):
            await self.view.update_message(interaction)


class MenuSelect(discord.ui.Select):
    """
    練習メニューを選択するためのセレクトメニュー。
    """

    def __init__(self):
        options = [
            discord.SelectOption(
                label="筋トレ",
                value="strength",
                emoji="🏋️",
                description="攻撃と防御を重視した肉体改造。体が重くなることも。",
            ),
            discord.SelectOption(
                label="走り込み",
                value="running",
                emoji="🏃",
                description="回避と行動力を鍛える基礎訓練。スタミナは使わない。",
            ),
            discord.SelectOption(
                label="受け身",
                value="ukemi",
                emoji="🛡️",
                description="防御と生命力を高める防御訓練。回避がおろそかになるかも。",
            ),
            discord.SelectOption(
                label="シャドーボクシング",
                value="shadow",
                emoji="🥊",
                description="流れるような連撃を想定した実戦訓練。消耗が激しい。",
            ),
            discord.SelectOption(
                label="スパーリング",
                value="sparring",
                emoji="⚔️",
                description="全能力を平均的に高める実戦形式。効率はやや悪い。",
            ),
            discord.SelectOption(
                label="マッサージ・お昼寝",
                value="massage",
                emoji="💤",
                description="休息とケア。疲労を回復し、オーバーワークのリスクもない。",
            ),
        ]
        super().__init__(
            placeholder="練習メニューを選択してください...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_menu = self.values[0]
        if hasattr(self.view, "update_message"):
            await self.view.update_message(interaction)


from core.ui.view_base import BaseModal, BaseView


class DobumonBaseView(BaseView):
    """
    怒武者関連のViewの基底クラス。
    本人確認や共通のタイムアウト処理を行います。
    """

    def __init__(self, user: discord.User, timeout: float = 120.0):
        super().__init__(timeout=timeout)
        self.user = user

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """インタラクションを行ったユーザーがViewの所有者かチェックします。"""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("⚠️ 本人のみ操作可能です。", ephemeral=True)
            return False
        return True


class DobumonBaseModal(BaseModal):
    """
    怒武者関連のモーダルの基底クラス。
    """

    pass
