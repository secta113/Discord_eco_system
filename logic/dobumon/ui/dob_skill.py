from typing import TYPE_CHECKING, Callable, Dict, List, Optional

import discord

from .dob_common import DobumonBaseModal, DobumonBaseView, DobumonSelect

if TYPE_CHECKING:
    from logic.dobumon.core.dob_models import Dobumon


class RenameSkillModal(DobumonBaseModal, title="技の命名"):
    """
    技の名前を変更するためのモーダル。
    """

    name_input = discord.ui.TextInput(
        label="新しい技名",
        placeholder="例: れんごく斬り",
        min_length=1,
        max_length=20,
        required=True,
    )

    def __init__(self, dobumon_id: str, slot_index: int, callback_func: Callable):
        super().__init__()
        self.dobumon_id = dobumon_id
        self.slot_index = slot_index
        self.callback_func = callback_func

    async def on_submit(self, interaction: discord.Interaction):
        await self.callback_func(
            interaction, self.dobumon_id, self.slot_index + 1, self.name_input.value
        )


class SkillSlotSelect(discord.ui.Select):
    """
    技スロットを選択するためのセレクトメニュー。
    """

    def __init__(self, skills: List[Dict]):
        options = []
        for i, s in enumerate(skills):
            label = f"Slot {i + 1}: {s['name']}"
            if s.get("is_named"):
                label += " (命名済)"
            options.append(
                discord.SelectOption(
                    label=label,
                    value=str(i),
                    description="このスロットの技を命名します",
                )
            )
        super().__init__(
            placeholder="命名するスロットを選択...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_slot_index = int(self.values[0])
        await self.view.update_message(interaction)


class RenameSkillView(DobumonBaseView):
    """
    習得した技を命名するためのウィザード。
    """

    def __init__(
        self,
        user: discord.User,
        dobumons: List["Dobumon"],
        callback_func: Callable,
        timeout: float = 120.0,
    ):
        super().__init__(user=user, timeout=timeout)
        self.dobumons = dobumons
        self.callback_func = callback_func
        self.selected_dobumon_id: Optional[str] = None
        self.selected_slot_index: Optional[int] = None

        self.dobumon_select = DobumonSelect(dobumons, "命名対象の怒武者を選択...")
        self.add_item(self.dobumon_select)

    async def update_message(self, interaction: discord.Interaction):
        dobu = next((d for d in self.dobumons if d.dobumon_id == self.selected_dobumon_id), None)

        self.clear_items()
        self.add_item(self.dobumon_select)
        for opt in self.dobumon_select.options:
            opt.default = opt.value == self.selected_dobumon_id

        embed = discord.Embed(
            title="🏷️ 技の命名ウィザード",
            description="対象の怒武者と命名する技スロットを選択してください。",
            color=0x9B59B6,
        )

        if dobu:
            if not dobu.skills:
                embed.description = f"❌ **{dobu.name}** はまだ技を習得していません。"
            else:
                slot_select = SkillSlotSelect(dobu.skills)
                for opt in slot_select.options:
                    opt.default = self.selected_slot_index is not None and opt.value == str(
                        self.selected_slot_index
                    )
                self.add_item(slot_select)

                self.confirm_button.disabled = self.selected_slot_index is None
                self.add_item(self.confirm_button)

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="名前を決定する", style=discord.ButtonStyle.success, disabled=True)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        modal = RenameSkillModal(
            self.selected_dobumon_id, self.selected_slot_index, self.callback_func
        )
        await interaction.response.send_modal(modal)
        self.stop()
