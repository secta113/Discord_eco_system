import discord
from discord import ui

from core.economy import wallet
from core.ui.view_base import BaseModal

from .dob_common import DobumonBaseView
from .dob_formatter import DobumonFormatter


class DobumonNameModal(BaseModal):
    """
    怒武者の名前を入力するモーダル。
    """

    def __init__(self, title: str, callback: callable):
        super().__init__(title=title)
        self.callback = callback
        self.name_input = ui.TextInput(
            label="怒武者の名前",
            placeholder="例: ドブモン1号",
            min_length=1,
            max_length=20,
            required=True,
        )
        self.add_item(self.name_input)

    async def on_submit(self, interaction: discord.Interaction):
        await self.callback(interaction, self.name_input.value)


class DobumonBuyView(DobumonBaseView):
    """
    ショップ選択、性別・属性選択、プレビューを経て怒武者を購入するウィザードView。
    """

    def __init__(self, user: discord.User, buy_service):
        super().__init__(user=user, timeout=180)
        self.buy_service = buy_service
        self.manager = buy_service.manager

        self.shop_id = None
        self.gender = None
        self.attribute = None
        self.preview_data = None

        # 最初のステップを表示
        self.setup_shop_selection()

    def setup_shop_selection(self):
        """ステップ1: ショップの選択"""
        self.clear_items()
        from logic.dobumon.core.dob_buy_service import SHOP_CONFIGS

        options = []
        for sid, config in SHOP_CONFIGS.items():
            options.append(
                discord.SelectOption(
                    label=config["name"],
                    value=sid,
                    description=f"{config['price']:,} pts",
                    emoji=config["emoji"],
                )
            )

        select = ui.Select(placeholder="購入するショップを選択してください", options=options)
        select.callback = self.on_shop_select
        self.add_item(select)

    async def on_shop_select(self, interaction: discord.Interaction):
        self.shop_id = interaction.data["values"][0]
        config = self.buy_service.get_shop_config(self.shop_id)

        # 購入制限チェック
        if not self.buy_service.check_purchase_limit(interaction.user.id, self.shop_id):
            await interaction.response.send_message(
                f"❌ 「{config['name']}」での本日の購入上限に達しています。明日またお越しください。",
                ephemeral=True,
            )
            return

        self.setup_configuration()
        await self.update_view(interaction)

    def setup_configuration(self):
        """ステップ2: 性別と属性の選択"""
        self.clear_items()

        # 性別選択
        gender_select = ui.Select(
            placeholder="性別を選択してください",
            options=[
                discord.SelectOption(label="オス (♂)", value="M", emoji="♂"),
                discord.SelectOption(label="メス (♀)", value="F", emoji="♀"),
            ],
            row=0,
        )
        gender_select.callback = self.on_gender_select
        self.add_item(gender_select)

        # 属性選択
        attr_select = ui.Select(
            placeholder="属性を選択してください",
            options=[
                discord.SelectOption(label="火属性", value="fire", emoji="🔥"),
                discord.SelectOption(label="水属性", value="water", emoji="💧"),
                discord.SelectOption(label="草属性", value="grass", emoji="🌿"),
            ],
            row=1,
        )
        attr_select.callback = self.on_attribute_select
        self.add_item(attr_select)

        # 次へボタン
        next_button = ui.Button(label="個体を確認する", style=discord.ButtonStyle.primary, row=2)
        next_button.callback = self.on_next_to_preview
        next_button.disabled = not (self.gender and self.attribute)
        self.add_item(next_button)

        # 戻るボタン
        back_button = ui.Button(label="戻る", style=discord.ButtonStyle.secondary, row=2)
        back_button.callback = self.on_back_to_shops
        self.add_item(back_button)

    async def on_gender_select(self, interaction: discord.Interaction):
        self.gender = interaction.data["values"][0]
        self.setup_configuration()
        await self.update_view(interaction)

    async def on_attribute_select(self, interaction: discord.Interaction):
        self.attribute = interaction.data["values"][0]
        self.setup_configuration()
        await self.update_view(interaction)

    async def on_next_to_preview(self, interaction: discord.Interaction):
        # プレビューデータの生成
        self.preview_data = self.buy_service.generate_preview(self.shop_id)
        self.setup_preview()
        await self.update_view(interaction)

    async def on_back_to_shops(self, interaction: discord.Interaction):
        self.shop_id = None
        self.gender = None
        self.attribute = None
        self.setup_shop_selection()
        await self.update_view(interaction)

    def setup_preview(self):
        """ステップ3: プレビューと最終確認"""
        self.clear_items()

        config = self.buy_service.get_shop_config(self.shop_id)

        buy_button = ui.Button(
            label=f"購入する ({config['price']:,} pts)",
            style=discord.ButtonStyle.success,
            row=0,
        )
        buy_button.callback = self.on_buy_click
        self.add_item(buy_button)

        cancel_button = ui.Button(label="選び直す", style=discord.ButtonStyle.danger, row=0)
        cancel_button.callback = self.on_back_to_config
        self.add_item(cancel_button)

    async def on_back_to_config(self, interaction: discord.Interaction):
        self.preview_data = None
        self.setup_configuration()
        await self.update_view(interaction)

    async def on_buy_click(self, interaction: discord.Interaction):
        modal = DobumonNameModal(title="怒武者の名前を入力", callback=self.process_purchase)
        await interaction.response.send_modal(modal)

    async def process_purchase(self, interaction: discord.Interaction, name: str):
        # 二重送信防止
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)

        try:
            dobu = await self.buy_service.execute_purchase(
                user_id=interaction.user.id,
                name=name,
                gender=self.gender,
                attribute=self.attribute,
                preview_data=self.preview_data,
            )

            config = self.buy_service.get_shop_config(self.shop_id)
            embed = discord.Embed(
                title=f"{config['emoji']} 怒武者 獲得！",
                color=config["color"],
            )
            embed.description = f"**{config['name']}** で **{dobu.name}** を購入しました。\n"
            embed.description += "━━━━━━ Status ━━━━━━\n"
            embed.description += DobumonFormatter.get_stat_grid(dobu, is_owner=False)
            embed.add_field(
                name="残高",
                value=f"{wallet.load_balance(interaction.user.id):,} pts",
                inline=False,
            )

            await interaction.edit_original_response(embed=embed, view=None)

            # 詳細ステータス送信
            status_embed = DobumonFormatter.format_status_embed(dobu, is_owner=True)
            status_embed.title = f"✨ {dobu.name} の素質を確認しました"
            await interaction.followup.send(embed=status_embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ 購入中にエラーが発生しました: {e}", ephemeral=True)
            # 必要に応じてビューを復旧
            for item in self.children:
                item.disabled = False
            await interaction.edit_original_response(view=self)

    async def update_view(self, interaction: discord.Interaction):
        embed = self.create_embed()
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    def create_embed(self) -> discord.Embed:
        if not self.shop_id:
            embed = discord.Embed(
                title="🛒 怒武者ショップ選択",
                description="購入したい怒武者を扱うショップを選択してください。",
                color=0x2ECC71,
            )
            from logic.dobumon.core.dob_buy_service import SHOP_CONFIGS

            for _sid, config in SHOP_CONFIGS.items():
                embed.add_field(
                    name=f"{config['emoji']} {config['name']} ({config['price']:,} pts)",
                    value=config["description"],
                    inline=False,
                )
            return embed

        config = self.buy_service.get_shop_config(self.shop_id)
        embed = discord.Embed(
            title=f"{config['emoji']} {config['name']} - 個体選択",
            color=config["color"],
        )

        if not self.preview_data:
            desc = "性別と属性を選択してください。\n\n"
            if self.gender:
                g = "オス (♂)" if self.gender == "M" else "メス (♀)"
                desc += f"👤 性別: **{g}**\n"
            if self.attribute:
                a = {"fire": "🔥 火", "water": "💧 水", "grass": "🌿 草"}.get(self.attribute)
                desc += f"✨ 属性: **{a}**\n"
            embed.description = desc
        else:
            embed.title = f"{config['emoji']} {config['name']} - 最終確認"
            embed.description = (
                f"こちらの個体を購入しますか？\n\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"👤 性別: **{'オス (♂)' if self.gender == 'M' else 'メス (♀)'}**\n"
                f"✨ 属性: **{ {'fire': '🔥 火', 'water': '💧 水', 'grass': '🌿 草'}[self.attribute] }**\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"🔍 **鑑定士の言葉:**\n"
                f"*{self.preview_data['hint']}*\n"
                f"━━━━━━━━━━━━━━━━\n"
            )

        balance = wallet.load_balance(self.user.id)
        embed.set_footer(text=f"現在の所持ポイント: {balance:,} pts")

        return embed
