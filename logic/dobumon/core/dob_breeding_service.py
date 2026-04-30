import discord

from core.economy import wallet
from logic.dobumon.core.dob_exceptions import (
    DobumonExecutionError,
    DobumonInsufficientPointsError,
)
from logic.dobumon.core.dob_logger import DobumonLogger
from logic.dobumon.core.dob_manager import DobumonManager
from logic.dobumon.dob_views import (
    DobumonFormatter,
)


class DobumonBreedingService:
    """
    怒武者の交配実行ロジックを管理するサービス。
    """

    def __init__(self, manager: DobumonManager):
        self.manager = manager

    async def execute_breed(
        self, interaction: discord.Interaction, p1_id: str, p2_id: str, name: str
    ):
        """交配の実行ロジック本体"""
        user_id = interaction.user.id
        cost = 20000
        balance = wallet.load_balance(user_id)
        if balance < cost:
            raise DobumonInsufficientPointsError(cost, balance)

        result = self.manager.breed_dobumon(p1_id, p2_id, name)
        if not result["success"]:
            raise DobumonExecutionError(f"交配に失敗しました: {result['msg']}")

        balance = wallet.load_balance(user_id)
        wallet.save_balance(user_id, balance - cost)
        wallet.add_history(user_id, "怒武者交配費用", -cost)
        child = result["child"]
        p1_name = result["p1_name"]
        p2_name = result["p2_name"]

        embed = discord.Embed(
            title="🧬 命の連鎖（交配完了）",
            description=f"**{p1_name}** と **{p2_name}** の魂が合わさり、新しい命が誕生しました！",
            color=discord.Color.gold(),
        )
        embed.add_field(name="名前", value=child.name, inline=True)
        embed.add_field(
            name="性別", value="オス (M)" if child.gender == "M" else "メス (F)", inline=True
        )
        embed.add_field(name="属性", value=child.attribute, inline=True)
        embed.add_field(name="世代", value=f"第 {child.generation} 世代", inline=True)
        # 公開メッセージからは具体的な数値を削除
        embed.description += "\n━━━━━━ Initial Status ━━━━━━\n"
        embed.description += DobumonFormatter.get_stat_grid(child, is_owner=False)

        traits = []
        if child.is_sterile:
            traits.append("⚠️ 生殖機能なし（薔薇の宿命）")
        if not child.can_extend_lifespan:
            traits.append("🖤 延命アイテム使用不可")
        if child.illness_rate >= 0.1:
            traits.append("🌡️ 極めて病弱")
        elif child.illness_rate > 0.01:
            traits.append("🩺 病弱傾向")
        if traits:
            embed.add_field(name="固有特性", value="\n".join(traits), inline=False)

        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=None)
        else:
            await interaction.response.send_message(embed=embed)

        # 所有者にのみ詳細なステータスを送信
        status_embed = DobumonFormatter.format_status_embed(child, is_owner=True)
        status_embed.title = f"🐣 {child.name} の素質を確認しました"
        await interaction.followup.send(embed=status_embed, ephemeral=True)

        DobumonLogger.action(
            interaction.user.display_name, "bred", f"{p1_name} + {p2_name}", f"-> {child.name}"
        )
