from typing import Any, List, Optional

import discord

from logic.dobumon.core.dob_models import Dobumon

from .dob_common import DobumonBaseView


class DobumonMapSelectionView(DobumonBaseView):
    """
    mapコマンドの最初のステップで表示する、対象個体を選択するためのView。
    """

    def __init__(
        self,
        user: discord.User,
        all_dobumons: List[Dobumon],
        display_dobumons: List[Dobumon],
        repo: Any,
        timeout: float = 300.0,
    ):
        super().__init__(user=user, timeout=timeout)
        self.all_dobumons = all_dobumons
        self.display_dobumons = display_dobumons
        self.repo = repo

        # セレクトメニューの構築
        options = []
        for dobu in self.display_dobumons:
            attr_emoji = {"fire": "🔥", "water": "💧", "grass": "🌿"}.get(dobu.attribute, "⚔️")
            gender_icon = "♂️" if dobu.gender == "M" else "♀️"

            # 状態（生存・死亡・売却）の判定
            status_suffix = ""
            if not dobu.is_alive:
                if getattr(dobu, "is_sold", False):
                    status_suffix = " (💰売却)"
                else:
                    status_suffix = " (💀死亡)"

            label = f"{dobu.name} (Gen {dobu.generation}){status_suffix}"
            description = f"{dobu.attribute.upper()} | {gender_icon} | {dobu.life_stage}"

            options.append(
                discord.SelectOption(
                    label=label,
                    value=dobu.dobumon_id,
                    description=description,
                    emoji=attr_emoji,
                )
            )

        # 選択肢が多い場合は制限（Discordの仕様: 25件まで）
        if len(options) > 25:
            options = options[:25]

        select = discord.ui.Select(
            placeholder="マップを表示する怒武者を選択...",
            options=options,
            custom_id="map_target_select",
        )
        select.callback = self.on_select
        self.add_item(select)

    async def on_select(self, interaction: discord.Interaction):
        # 循環参照を避けるため動的インポート
        from logic.dobumon.dob_views.dob_kinship_tree import DobumonKinshipTree

        await interaction.response.defer()

        selected_id = interaction.data["values"][0]

        # マップ生成
        canvas = DobumonKinshipTree()
        image_buf = canvas.render_pedigree_map(
            self.user.display_name,
            self.all_dobumons,
            self.user.id,
            repo=self.repo,
            target_ids=[selected_id],
        )

        file = discord.File(fp=image_buf, filename="dobumon_pedigree.png")

        embed = discord.Embed(
            title="〓 怒武者 血統地図（親等図） 〓",
            description=f"**{self.user.display_name}** の所持ドブモンの家系図です。\n\n**【サンプルブリーディング】**",
            color=0x34495E,
        )
        embed.set_image(url="attachment://dobumon_pedigree.png")

        # 生存個体のみを抽出してサンプルブリーディングViewへ移行
        alive_dobumons = [d for d in self.all_dobumons if d.is_alive]
        next_view = MapSampleBreedView(self.user, self.all_dobumons, alive_dobumons, self.repo)

        await interaction.edit_original_response(embed=embed, attachments=[file], view=next_view)


class MapSampleBreedView(DobumonBaseView):
    """
    mapコマンドでサンプルブリーディング（親等表示）を行うためのView。
    循環参照を避けるため、ロジックはメソッド内で動的にインポートします。
    """

    def __init__(
        self,
        user: discord.User,
        all_dobumons: List[Dobumon],
        alive_dobumons: List[Dobumon],
        repo: Any,
        timeout: float = 300.0,
    ):
        super().__init__(user=user, timeout=timeout)
        self.all_dobumons = all_dobumons
        self.alive_dobumons = alive_dobumons
        self.repo = repo
        self.p1_id: Optional[str] = None
        self.p2_id: Optional[str] = None

        # 親選択ドロップダウンの追加
        from logic.dobumon.dob_views.dob_breeding import Parent1Select, Parent2Select

        if alive_dobumons:
            self.add_item(Parent1Select(alive_dobumons))
            self.add_item(Parent2Select(alive_dobumons))

    async def update_message(self, interaction: discord.Interaction):
        await interaction.response.defer()

        from logic.dobumon.dob_views.dob_breeding import BreedSelectBaseView
        from logic.dobumon.dob_views.dob_kinship_tree import DobumonKinshipTree

        # 選択中の個体情報を取得
        p1 = next((d for d in self.all_dobumons if d.dobumon_id == self.p1_id), None)
        p2 = next((d for d in self.all_dobumons if d.dobumon_id == self.p2_id), None)

        # 共通ロジックを使って説明文を生成
        base_logic = BreedSelectBaseView(self.user, self.alive_dobumons)
        base_logic.p1_id = self.p1_id
        base_logic.p2_id = self.p2_id
        kinship_desc = base_logic.get_kinship_description(p1, p2)

        desc = f"**{self.user.display_name}** の所持ドブモンの家系図です。\n\n**【サンプルブリーディング】**\n\n"
        desc += kinship_desc

        target_ids = []
        if self.p1_id:
            target_ids.append(self.p1_id)
        if self.p2_id:
            target_ids.append(self.p2_id)
        if not target_ids:
            target_ids = None

        canvas = DobumonKinshipTree()
        image_buf = canvas.render_pedigree_map(
            self.user.display_name,
            self.all_dobumons,
            self.user.id,
            repo=self.repo,
            target_ids=target_ids,
        )

        file = discord.File(fp=image_buf, filename="dobumon_pedigree.png")

        embed = discord.Embed(
            title="〓 怒武者 血統地図（親等図） 〓",
            description=desc,
            color=0x34495E,
        )
        embed.set_image(url="attachment://dobumon_pedigree.png")

        await interaction.edit_original_response(embed=embed, attachments=[file], view=self)
