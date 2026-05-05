import discord
from discord import app_commands
from discord.ext import commands

from core.economy import wallet
from core.utils.decorators import check_maintenance, defer_response
from core.utils.formatters import f_bold_pts, f_pts
from logic.bet_service import BetService
from logic.economy.jackpot import JackpotService
from logic.economy.provider import EconomyProvider
from logic.gacha_service import gacha_service


class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    wallet_group = app_commands.Group(
        name="dd-wallet", description="ポイント・統計・残高確認関連のコマンド"
    )

    @wallet_group.command(name="balance", description="現在の残高を確認します")
    @defer_response(ephemeral=True)
    async def balance(self, interaction: discord.Interaction):
        bal = wallet.load_balance(interaction.user.id)
        await interaction.followup.send(
            f"🪙 {interaction.user.mention} さんの現在の残高は {f_bold_pts(bal)} です。",
            ephemeral=True,
        )

    @wallet_group.command(
        name="jackpot", description="現在のシステムジャックポットプールを確認します"
    )
    @defer_response(ephemeral=True)
    async def jackpot(self, interaction: discord.Interaction):
        jp_amount = JackpotService.get_pool_balance()
        embed = discord.Embed(
            title="🎰 システム・ジャックポット",
            description=f"現在のプール額: {f_bold_pts(jp_amount)}\n\n(※対システム戦でのプレイヤーの消費分等がプールされ、今後のシステム還元等に利用されます)",
            color=0xE67E22,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @wallet_group.command(name="stats", description="戦績と獲得バッジ一覧を表示します")
    @defer_response(ephemeral=True)
    async def stats(self, interaction: discord.Interaction):
        target = interaction.user
        stats = wallet.get_stats(target.id)
        bal = wallet.load_balance(target.id)

        embed = discord.Embed(title=f"📊 {target.display_name} のプロフィール", color=0x9B59B6)
        embed.add_field(name="所持ポイント", value=f_pts(bal), inline=False)
        embed.add_field(name="累計参加回数", value=f"{stats['games_played']} 回", inline=True)
        embed.add_field(name="累計勝利回数", value=f"{stats['total_wins']} 回", inline=True)
        embed.add_field(name="最大一撃配当", value=f_pts(stats["max_win_amount"]), inline=True)

        if stats["games_played"] > 0:
            win_rate = (stats["total_wins"] / stats["games_played"]) * 100
            embed.set_footer(text=f"勝率: {win_rate:.1f}%")

        # ガチャコンプリート率の追加
        collected, total, percentage = gacha_service.get_completion_info(target.id)
        if total > 0:
            embed.add_field(
                name="ガチャ図鑑", value=f"{collected} / {total} ({percentage:.1f}%)", inline=False
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @wallet_group.command(name="daily", description="デイリーボーナスを受け取ります")
    @check_maintenance()
    @defer_response(ephemeral=True)
    async def daily(self, interaction: discord.Interaction):
        message = BetService.claim_daily(interaction.user.id)
        await interaction.followup.send(message, ephemeral=True)

    @wallet_group.command(name="pay", description="指定したユーザーに自分のポイントを送ります")
    @app_commands.describe(target="送信先ユーザー", amount="送るポイント数")
    @check_maintenance()
    @defer_response(ephemeral=True)
    async def pay(self, interaction: discord.Interaction, target: discord.Member, amount: int):
        if amount <= 0:
            return await interaction.followup.send(
                "ポイントは1以上を指定してください。", ephemeral=True
            )
        if interaction.user.id == target.id:
            return await interaction.followup.send(
                "自分自身に送ることはできません。", ephemeral=True
            )

        # EconomyProvider.escrow が残高不足時に例外を投げるため、明示的なチェックは不要
        EconomyProvider.escrow(
            interaction.user.id, amount, reason=f"ポイント送付 to {target.display_name}"
        )

        to_bal = wallet.load_balance(target.id)
        wallet.save_balance(target.id, to_bal + amount)
        wallet.add_history(target.id, f"ポイント受領 from {interaction.user.display_name}", amount)

        from_bal_after = wallet.load_balance(interaction.user.id)
        await interaction.followup.send(
            f"💸 {target.mention} に {f_pts(amount)} を送りました。(あなたの残高: {f_pts(from_bal_after)})"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Economy(bot))
