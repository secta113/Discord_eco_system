from typing import Callable, List, Optional

import discord

from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.dob_views.dob_common import DobumonBaseView, DobumonSelect

from .wild_config import WildBattleConfig


class WildBattleWizard(DobumonBaseView):
    """
    野生戦の各種設定（ドブモン、難易度、マップ）を行うウィザード形式のView。
    """

    def __init__(self, user: discord.User, dobumons: List[Dobumon], callback: Callable):
        super().__init__(user=user, timeout=120.0)
        self.dobumons = dobumons
        self.callback = callback

        self.selected_dobumon_id: Optional[str] = None
        self.selected_rank: Optional[str] = None
        self.selected_map_id: Optional[str] = None

        self.step = "DOBUMON"  # DOBUMON -> RANK -> MAP
        self._setup_step()

    def _setup_step(self):
        self.clear_items()

        if self.step == "DOBUMON":
            select = DobumonSelect(self.dobumons, "使用する怒武者を選択...")
            select.callback = self._on_dobumon_select
            # 初期値のセット
            if self.selected_dobumon_id:
                for option in select.options:
                    option.default = option.value == self.selected_dobumon_id
            self.add_item(select)

        elif self.step == "RANK":
            ranks = WildBattleConfig.get_ranks()
            options = []
            for key, info in ranks.items():
                options.append(
                    discord.SelectOption(
                        label=info["name"],
                        value=key,
                        description=info["description"],
                        default=(key == self.selected_rank),
                    )
                )

            select = discord.ui.Select(placeholder="難易度（ランク）を選択...", options=options)
            select.callback = self._on_rank_select
            self.add_item(select)

        elif self.step == "MAP":
            # 選択されたランクに応じたマップを取得
            maps = WildBattleConfig.get_maps(self.selected_rank)
            options = []
            for m in maps:
                options.append(
                    discord.SelectOption(
                        label=f"{m['emoji']} {m['name']}",
                        value=m["id"],
                        description=m["description"],
                        default=(m["id"] == self.selected_map_id),
                    )
                )

            select = discord.ui.Select(placeholder="目的地（マップ）を選択...", options=options)
            select.callback = self._on_map_select
            self.add_item(select)

        # 戻るボタン (最初のステップ以外)
        if self.step != "DOBUMON":
            back_btn = discord.ui.Button(label="戻る", style=discord.ButtonStyle.secondary)
            back_btn.callback = self._on_back
            self.add_item(back_btn)

    def create_embed(self) -> discord.Embed:
        if self.step == "DOBUMON":
            return discord.Embed(
                title="🌳 野生戦ウィザード (1/3)",
                description="まずは戦わせる怒武者を選んでください。",
                color=0x2ECC71,
            )
        elif self.step == "RANK":
            return discord.Embed(
                title="📊 難易度選択 (2/3)",
                description="挑戦するランクを選択してください。\n高ランクほど敵は強大ですが、得られる報酬も莫大になります。",
                color=0x3498DB,
            )
        elif self.step == "MAP":
            rank_info = WildBattleConfig.get_rank(self.selected_rank)
            return discord.Embed(
                title="📍 目的地選択 (3/3)",
                description=f"**{rank_info['name']}** での戦場を選んでください。\nマップによって出現する属性が異なります。\n\n*※不利な属性で勝利するとボーナスが発生します！*",
                color=0xE67E22,
            )

    async def _on_dobumon_select(self, interaction: discord.Interaction):
        self.selected_dobumon_id = interaction.data["values"][0]
        self.step = "RANK"
        self._setup_step()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    async def _on_rank_select(self, interaction: discord.Interaction):
        self.selected_rank = interaction.data["values"][0]
        self.step = "MAP"
        self._setup_step()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    async def _on_map_select(self, interaction: discord.Interaction):
        self.selected_map_id = interaction.data["values"][0]
        self.stop()

        # 最終的な実行（service.execute_wild_battleへ戻る）
        await self.callback(
            interaction, self.selected_dobumon_id, self.selected_rank, self.selected_map_id
        )

    async def _on_back(self, interaction: discord.Interaction):
        if self.step == "RANK":
            self.step = "DOBUMON"
        elif self.step == "MAP":
            self.step = "RANK"

        self._setup_step()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)
