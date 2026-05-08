import math

import discord

from core.economy import wallet
from core.utils.formatters import f_bold_pts, f_pts
from logic.dobumon.core.dob_exceptions import (
    DobumonExecutionError,
    DobumonNotFoundError,
)
from logic.dobumon.core.dob_logger import DobumonLogger
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
        ハイパーインフレ対策として、高ステータス・高世代個体の価格上昇を非線形（平方根）に抑制。
        また、ライフステージによる価値の変動（老衰による大幅減額）を導入。
        """
        total_stats = dobu.hp + dobu.atk + dobu.defense + dobu.eva + dobu.spd

        # 1. 基本価格
        base_price = 5000

        # 2. ステータスボーナス (平方根による減衰)
        # 10k stats -> 100k pts, 1M stats -> 1M pts, 4M stats -> 2M pts
        stat_bonus = int(math.sqrt(total_stats) * 1000)

        # 3. 世代ボーナス (緩やかな上昇)
        generation_bonus = (dobu.generation - 1) * 500 + int(math.sqrt(dobu.generation) * 2000)

        # 4. 懐き度ボーナス
        affection_bonus = dobu.affection * 50

        initial_price = base_price + stat_bonus + generation_bonus + affection_bonus

        # 5. ライフステージ補正 (全盛期は価値が高く、老衰個体は買い叩かれる)
        stage_multipliers = {"young": 0.8, "prime": 1.2, "senior": 0.6, "twilight": 0.2}
        stage_mult = stage_multipliers.get(dobu.life_stage, 1.0)
        price = initial_price * stage_mult

        # 6. 禁忌深度による減額 (1層につき15%減、最大90%減)
        forbidden_depth = dobu.genetics.get("forbidden_depth", 0)
        reduction_rate = min(0.9, forbidden_depth * 0.15)
        final_price = int(price * (1.0 - reduction_rate))

        return max(500, final_price)

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
            description=f"**{dobu.name}** をドブ街のバイヤーに売却しました。\n\n獲得: {f_bold_pts(price)}",
            color=0xF1C40F,
        )
        embed.add_field(name="現在の残高", value=f_pts(wallet.load_balance(user_id)))

        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=None)
        else:
            await interaction.response.send_message(embed=embed)

        DobumonLogger.market(interaction.user.display_name, "sold", dobu, price)

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

        DobumonLogger.action(
            interaction.user.display_name, "renamed skill of", dobumon_id, f"to '{new_name}'"
        )
