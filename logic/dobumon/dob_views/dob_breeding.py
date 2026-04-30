from typing import TYPE_CHECKING, Callable, List, Optional

import discord

from logic.dobumon.genetics.dob_kinship import KinshipLogic

from .dob_common import DobumonBaseModal, DobumonBaseView

if TYPE_CHECKING:
    from logic.dobumon.core.dob_models import Dobumon


class BreedNameModal(DobumonBaseModal, title="怒武者の命名"):
    """
    交配後の子供に名前を付けるためのモーダル。
    """

    name_input = discord.ui.TextInput(
        label="子供の名前",
        placeholder="例: ムシャマル",
        min_length=1,
        max_length=20,
        required=True,
    )

    def __init__(self, p1_id: str, p2_id: str, callback_func: Callable):
        super().__init__()
        self.p1_id = p1_id
        self.p2_id = p2_id
        self.callback_func = callback_func

    async def on_submit(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.p1_id, self.p2_id, self.name_input.value)


class Parent1Select(discord.ui.Select):
    def __init__(self, dobumons: List["Dobumon"]):
        options = [
            discord.SelectOption(
                label=f"{d.name} ({'♂' if d.gender == 'M' else '♀'})", value=d.dobumon_id
            )
            for d in dobumons
        ]
        if len(options) > 25:
            options = options[:25]
        super().__init__(placeholder="親1を選択...", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        self.view.p1_id = self.values[0]
        for option in self.options:
            option.default = option.value == self.view.p1_id
        await self.view.update_message(interaction)


class Parent2Select(discord.ui.Select):
    def __init__(self, dobumons: List["Dobumon"]):
        options = [
            discord.SelectOption(
                label=f"{d.name} ({'♂' if d.gender == 'M' else '♀'})", value=d.dobumon_id
            )
            for d in dobumons
        ]
        if len(options) > 25:
            options = options[:25]
        super().__init__(placeholder="親2を選択...", options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        self.view.p2_id = self.values[0]
        for option in self.options:
            option.default = option.value == self.view.p2_id
        await self.view.update_message(interaction)


class BreedSelectBaseView(DobumonBaseView):
    """
    親選択の共通処理を持つBaseView。
    """

    def __init__(self, user: discord.User, dobumons: List["Dobumon"], timeout: float = 120.0):
        super().__init__(user=user, timeout=timeout)
        self.dobumons = dobumons
        self.p1_id: Optional[str] = None
        self.p2_id: Optional[str] = None

        if dobumons:
            self.p1_select = Parent1Select(dobumons)
            self.p2_select = Parent2Select(dobumons)
            self.add_item(self.p1_select)
            self.add_item(self.p2_select)

    def get_kinship_description(self, p1: Optional["Dobumon"], p2: Optional["Dobumon"]) -> str:
        desc = ""
        if p1 or p2:
            desc += "━━━━━━━━━━━━━━━━\n"
            p1_text = f"{p1.name} ({'♂' if p1.gender == 'M' else '♀'})" if p1 else "未選択"
            p2_text = f"{p2.name} ({'♂' if p2.gender == 'M' else '♀'})" if p2 else "未選択"
            desc += f"👤 親1: **{p1_text}**\n"
            desc += f"👤 親2: **{p2_text}**\n"
            desc += "━━━━━━━━━━━━━━━━\n"

        if self.p1_id and self.p2_id:
            if self.p1_id == self.p2_id:
                desc += "\n⚠️ **同じ個体同士は交配できません！**"
            elif p1 and p2:
                # 親等とCOIの計算
                p1_parsed = KinshipLogic.parse_lineage(p1.lineage)
                p2_parsed = KinshipLogic.parse_lineage(p2.lineage)
                degree = KinshipLogic.get_kinship_degree(
                    p1.dobumon_id, p1_parsed, p2.dobumon_id, p2_parsed
                )
                coi = KinshipLogic.calculate_coi(p1.dobumon_id, p1_parsed, p2.dobumon_id, p2_parsed)

                desc += "\n🧬 **遺伝子情報**\n"
                if degree is not None:
                    desc += f"├─ 親等: **{degree}親等**\n"
                else:
                    desc += "├─ 親等: **なし（他赤）**\n"

                desc += f"└─ 係数 (COI): **{coi * 100:.2f}%**\n"

                # 警告とペナルティ予測
                if degree is not None and degree <= 5:
                    penalties = KinshipLogic.calculate_inbreeding_penalties(coi)
                    desc += "\n⚠️ **近親配合の警告**\n"
                    desc += f"└ 寿命予測: **-{penalties['lifespan_penalty_pct']}%** / 病気率: **+{penalties['illness_gain_pct']}%**\n"
                    desc += "*※5親等以内の配合にはデメリットが発生します。*"

                if p1.gender == p2.gender:
                    desc += "\n⚠️ **血が禁忌に染まります（同性配合）**"

        return desc


class BreedSelectView(BreedSelectBaseView):
    """
    交配の両親を選択するためのView。
    """

    def __init__(
        self,
        user: discord.User,
        dobumons: List["Dobumon"],
        callback_func: Callable,
        timeout: float = 120.0,
    ):
        super().__init__(user=user, dobumons=dobumons, timeout=timeout)
        self.callback_func = callback_func

    async def update_message(self, interaction: discord.Interaction):
        # ボタンの有効化判定
        self.next_button.disabled = not (self.p1_id and self.p2_id and self.p1_id != self.p2_id)

        # 選択中の個体情報を取得
        p1 = next((d for d in self.dobumons if d.dobumon_id == self.p1_id), None)
        p2 = next((d for d in self.dobumons if d.dobumon_id == self.p2_id), None)

        desc = "交配させる両親を選択してください。\n費用: **20,000 pts**\n\n"
        desc += self.get_kinship_description(p1, p2)

        embed = discord.Embed(
            title="🧬 交配ウィザード",
            description=desc,
            color=discord.Color.gold()
            if not (
                self.p1_id
                and self.p2_id
                and p1
                and p2
                and KinshipLogic.get_kinship_degree(
                    p1.dobumon_id,
                    KinshipLogic.parse_lineage(p1.lineage),
                    p2.dobumon_id,
                    KinshipLogic.parse_lineage(p2.lineage),
                )
                is not None
                and KinshipLogic.get_kinship_degree(
                    p1.dobumon_id,
                    KinshipLogic.parse_lineage(p1.lineage),
                    p2.dobumon_id,
                    KinshipLogic.parse_lineage(p2.lineage),
                )
                <= 5
            )
            else discord.Color.orange(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="名前を決めて開始", style=discord.ButtonStyle.success, disabled=True, row=2
    )
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            BreedNameModal(self.p1_id, self.p2_id, self.callback_func)
        )
        self.stop()
