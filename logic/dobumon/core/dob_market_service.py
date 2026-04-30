import discord

from core.economy import wallet
from core.utils.logger import Logger
from logic.dobumon.core.dob_exceptions import (
    DobumonExecutionError,
    DobumonNotFoundError,
)
from logic.dobumon.core.dob_manager import DobumonManager
from logic.dobumon.core.dob_models import Dobumon


class DobumonMarketService:
    """
    怒武者の売却や命名など、市場・管理関連の実行ロジックを管理するサービス。
    """

    def __init__(self, manager: DobumonManager):
        self.manager = manager

    def calculate_sell_price(self, dobu: Dobumon) -> int:
        """売却価格を計算します。
        基本(10,000) + (合計ステータス * 5) + (懐き度 * 50) + (世代 - 1) * 2,000
        禁忌深度1につき10%減額。
        """
        total_stats = dobu.hp + dobu.atk + dobu.defense + dobu.eva + dobu.spd
        base_price = 10000
        stat_bonus = total_stats * 5
        affection_bonus = dobu.affection * 50
        generation_bonus = (dobu.generation - 1) * 2000

        initial_price = base_price + stat_bonus + affection_bonus + generation_bonus

        forbidden_depth = dobu.genetics.get("forbidden_depth", 0)
        reduction_rate = min(1.0, forbidden_depth * 0.1)
        final_price = int(initial_price * (1.0 - reduction_rate))

        return max(0, final_price)

    async def execute_sell(self, interaction: discord.Interaction, dobumon_id: str):
        """売却の実行ロジック本体"""
        user_id = interaction.user.id
        dobu = self.manager.get_dobumon(dobumon_id)
        if not dobu or str(dobu.owner_id) != str(user_id) or not dobu.is_alive:
            raise DobumonNotFoundError("有効な自分の怒武者が見つかりません。")

        price = self.calculate_sell_price(dobu)

        # 状態更新（論理削除）と保存
        dobu.sell()
        self.manager.save_dobumon(dobu)

        curr = wallet.load_balance(user_id)
        wallet.save_balance(user_id, curr + price)
        wallet.add_history(user_id, f"怒武者売却: {dobu.name}", price)

        embed = discord.Embed(
            title="💰 売却完了",
            description=f"**{dobu.name}** をドブ街のバイヤーに売却しました。\n\n獲得: **{price:,} pts**",
            color=0xF1C40F,
        )
        embed.add_field(name="現在の残高", value=f"{wallet.load_balance(user_id):,} pts")

        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=None)
        else:
            await interaction.response.send_message(embed=embed)

        Logger.info(
            "Dobumon",
            f"User {interaction.user.display_name} sold {dobumon_id} ({dobu.name}) for {price} pts",
        )

    async def execute_rename_skill(
        self, interaction: discord.Interaction, dobumon_id: str, slot: int, new_name: str
    ):
        """技の命名実行ロジック本体"""
        success, msg = self.manager.rename_skill(dobumon_id, slot - 1, new_name)
        if not success:
            raise DobumonExecutionError(msg)

        embed = discord.Embed(
            title="🏷️ 命名完了",
            description=f"技の名前を **{new_name}** に変更しました！",
            color=0x9B59B6,
        )
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        Logger.info(
            "Dobumon",
            f"User {interaction.user.display_name} renamed skill of {dobumon_id} to {new_name}",
        )
