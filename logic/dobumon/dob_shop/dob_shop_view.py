from typing import List, Optional

import discord
from discord import ui

from core.economy import wallet
from core.ui.view_base import BaseView
from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.dob_shop.dob_items import SHOPS, Shop, ShopItem, get_item_by_id, get_shop_by_id
from logic.dobumon.dob_shop.dob_shop_service import DobumonShopService
from logic.economy.status import StatusService


class DobumonShopView(BaseView):
    """
    怒武者（ドブモン）ショップ用のマルチステップView。
    1. ショップ選択 -> 2. 特徴表示＆決定 -> 3. アイテム＆対象選択 -> 4. 購入
    """

    def __init__(
        self,
        user: discord.User,
        shop_service: DobumonShopService,
        user_status: str,
        user_dobumons: List[Dobumon],
    ):
        super().__init__(timeout=300)
        self.user = user
        self.service = shop_service
        self.user_status = user_status
        self.user_dobumons = user_dobumons

        self.selected_shop: Optional[Shop] = None
        self.selected_item: Optional[ShopItem] = None
        self.selected_dobumon_id: Optional[str] = None

        self.step = 1  # 1: Shop Select, 2: Shop Detail, 3: Item/Target Select

        self._init_ui()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """
        このViewのすべてのボタン・セレクト操作の前に実行される権限チェック。
        """
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ 操作権限がありません。", ephemeral=True)
            return False
        return True

    def _init_ui(self):
        self.clear_items()

        if self.step == 1:
            self._add_shop_select()
        elif self.step == 2:
            self._add_shop_confirm()
        elif self.step == 3:
            self._add_item_target_select()

    def _add_shop_select(self):
        options = []
        for shop in SHOPS:
            # VIPショップも全員に表示する
            options.append(
                discord.SelectOption(
                    label=shop.name,
                    value=shop.shop_id,
                    description=shop.description[:50],
                    emoji="🛒" if not shop.is_vip else "💎",
                    default=(self.selected_shop and shop.shop_id == self.selected_shop.shop_id),
                )
            )

        select = ui.Select(
            placeholder="ショップを選択してください...", options=options, custom_id="shop_select"
        )
        select.callback = self.on_shop_select
        self.add_item(select)

    def _add_shop_confirm(self):
        # 戻るボタン
        back_btn = ui.Button(label="ショップ一覧に戻る", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.on_back_to_shops
        self.add_item(back_btn)

        # 決定ボタン
        confirm_btn = ui.Button(
            label=f"「{self.selected_shop.name}」に入る", style=discord.ButtonStyle.primary
        )
        confirm_btn.callback = self.on_shop_confirm
        self.add_item(confirm_btn)

    def _add_item_target_select(self):
        # アイテム選択
        item_options = [
            discord.SelectOption(
                label=f"{item.name} ({item.price:,} pts)",
                value=item.item_id,
                description=item.description[:50],
                default=(self.selected_item and item.item_id == self.selected_item.item_id),
            )
            for item in self.selected_shop.items
        ]
        item_select = ui.Select(
            placeholder="購入するアイテムを選択...",
            options=item_options,
            custom_id="item_select",
            row=0,
        )
        item_select.callback = self.on_item_select
        self.add_item(item_select)

        # 対象ドブモン選択
        if self.user_dobumons:
            dobu_options = [
                discord.SelectOption(
                    label=f"{d.name} (LV.{d.rank})",
                    value=d.dobumon_id,
                    description=f"HP:{int(d.hp)} ATK:{int(d.atk)}",
                    default=(d.dobumon_id == self.selected_dobumon_id),
                )
                for d in self.user_dobumons[:25]  # Discord上限
            ]
            dobu_select = ui.Select(
                placeholder="対象の怒武者を選択...",
                options=dobu_options,
                custom_id="target_select",
                row=1,
            )
            dobu_select.callback = self.on_target_select
            self.add_item(dobu_select)

        # 戻るボタン
        back_btn = ui.Button(label="ショップ選択に戻る", style=discord.ButtonStyle.secondary, row=2)
        back_btn.callback = self.on_back_to_shops
        self.add_item(back_btn)

        # 購入ボタン
        buy_btn = ui.Button(
            label="購入を確定する", style=discord.ButtonStyle.success, row=2, disabled=True
        )
        buy_btn.callback = self.on_buy_confirm
        self.buy_button = buy_btn
        self.add_item(buy_btn)

        self._update_buy_button_state()

    def _update_buy_button_state(self):
        if hasattr(self, "buy_button"):
            # アイテムが選択されていること、および（対象が必要なアイテムなら）対象が選択されていること
            if not self.selected_item:
                self.buy_button.disabled = True
                return

            # 全てのアイテムに対象が必要な仕様とする（アイテムによって不要な場合もあるが、実装のシンプルさのため）
            self.buy_button.disabled = not (self.selected_item and self.selected_dobumon_id)
            if self.selected_item:
                self.buy_button.label = (
                    f"購入: {self.selected_item.name} ({self.selected_item.price:,} pts)"
                )

    def create_embed(self) -> discord.Embed:
        embed = discord.Embed(title="🏪 怒武者アイテムショップ", color=0x3498DB)

        if self.step == 1:
            embed.description = "商店街にやってきました。どのショップに入りますか？\n（VIPショップはPrimeユーザーのみ入場可能です）"
        elif self.step == 2:
            embed.title = f"🏪 {self.selected_shop.name}"
            embed.description = f"**【店主の話】**\n「{self.selected_shop.description}」\n\nこのショップで買い物をしますか？"
        elif self.step == 3:
            embed.title = f"🛒 {self.selected_shop.name} - 商品棚"
            if self.selected_item:
                embed.description = f"**商品: {self.selected_item.name}**\n価格: **{self.selected_item.price:,} pts**\n効果: {self.selected_item.description}"
            else:
                embed.description = "購入するアイテムを選んでください。"

            if self.selected_dobumon_id:
                target_dobu = next(
                    (d for d in self.user_dobumons if d.dobumon_id == self.selected_dobumon_id),
                    None,
                )
                if target_dobu:
                    embed.add_field(name="対象", value=f"✅ {target_dobu.name}", inline=False)
            else:
                embed.add_field(
                    name="対象", value="❓ 未選択 (メニューから選んでください)", inline=False
                )

        return embed

    async def on_shop_select(self, interaction: discord.Interaction):
        # 資産ベンチマーク計算（全ユーザーの取得）が重いため defer
        await interaction.response.defer(ephemeral=True)

        shop_id = interaction.data["values"][0]
        shop = get_shop_by_id(shop_id)

        # VIP入店制限のチェック
        if shop.is_vip and self.user_status != "Prime":
            benchmark = StatusService.get_benchmark()
            balance = wallet.load_balance(interaction.user.id)
            missing = int(benchmark) + 1 - balance

            rejection_embed = discord.Embed(
                title="🚫 入店拒否",
                description="「VIP以外の入店はお断りしております。」",
                color=discord.Color.red(),
            )
            rejection_embed.add_field(name="現在のランク", value=self.user_status, inline=True)
            rejection_embed.add_field(name="不足ポイント", value=f"{missing:,} pts", inline=True)
            rejection_embed.set_footer(
                text="※Primeユーザーになるには所持金がベンチマークを超える必要があります。"
            )

            return await interaction.edit_original_response(embed=rejection_embed, view=None)

        self.selected_shop = shop
        self.step = 2
        self._init_ui()
        await interaction.edit_original_response(embed=self.create_embed(), view=self)

    async def on_back_to_shops(self, interaction: discord.Interaction):
        self.selected_shop = None
        self.selected_item = None
        self.step = 1
        self._init_ui()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    async def on_shop_confirm(self, interaction: discord.Interaction):
        self.step = 3
        self._init_ui()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    async def on_item_select(self, interaction: discord.Interaction):
        self.selected_item = get_item_by_id(interaction.data["values"][0])
        self._init_ui()
        self._update_buy_button_state()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    async def on_target_select(self, interaction: discord.Interaction):
        self.selected_dobumon_id = interaction.data["values"][0]
        self._init_ui()
        self._update_buy_button_state()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    async def on_buy_confirm(self, interaction: discord.Interaction):
        # 二重送信防止
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

        success, msg = await self.service.execute_purchase(
            user_id=self.user.id,
            item_id=self.selected_item.item_id,
            dobumon_id=self.selected_dobumon_id,
        )

        if success:
            embed = discord.Embed(title="✅ 購入完了", color=0x2ECC71, description=msg)
            await interaction.edit_original_response(embed=embed, view=None)
        else:
            # 失敗時はボタンを戻す
            for child in self.children:
                child.disabled = False
            self._update_buy_button_state()
            await interaction.edit_original_response(view=self)
            await interaction.followup.send(f"❌ 購入に失敗しました: {msg}", ephemeral=True)
