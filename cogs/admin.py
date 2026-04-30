from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from core.economy import wallet
from core.utils.config import START_TIME, VERSION
from core.utils.time_utils import get_jst_now


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    mod_group = app_commands.Group(name="dd-mod", description="【管理者用】システム・管理コマンド")

    @mod_group.command(name="maintenance", description="システムの緊急停止・再開を行います")
    @app_commands.describe(state="on:停止, off:再開")
    @app_commands.default_permissions(administrator=True)
    async def maintenance(self, interaction: discord.Interaction, state: Literal["on", "off"]):
        # bot instance に状態を保存するように変更
        self.bot.maintenance_mode = state == "on"
        status_text = "🔴 停止中 (ON)" if self.bot.maintenance_mode else "🟢 稼働中 (OFF)"
        await interaction.response.send_message(
            f"メンテナンスモードを **{status_text}** に変更しました。", ephemeral=True
        )

    @mod_group.command(name="logs", description="指定ユーザーの直近のポイント履歴を表示します")
    @app_commands.describe(target="対象ユーザー")
    @app_commands.default_permissions(administrator=True)
    async def logs(self, interaction: discord.Interaction, target: discord.Member):
        history = wallet.get_history(target.id)
        if not history:
            return await interaction.response.send_message(
                f"📜 {target.display_name} の履歴はありません。", ephemeral=True
            )

        lines = []
        for r in reversed(history[-15:]):
            amount_str = f"+{r['amount']}" if r["amount"] >= 0 else str(r["amount"])
            lines.append(f"`{r['date']}`: {r['reason']} ({amount_str} pts)")

        embed = discord.Embed(
            title=f"📜 {target.display_name} の履歴", description="\n".join(lines), color=0x3498DB
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @mod_group.command(
        name="status", description="システムの状態（バージョン、Uptime、総流通額）を表示します"
    )
    @app_commands.default_permissions(administrator=True)
    async def status(self, interaction: discord.Interaction):
        uptime = get_jst_now() - START_TIME
        days, seconds = uptime.days, uptime.seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        uptime_str = f"{days}日 {hours}時間 {minutes}分"

        all_bal = sum(wallet.get_all_balances().values())

        embed = discord.Embed(title="📊 システムステータス", color=0x2ECC71)
        embed.add_field(name="バージョン", value=VERSION, inline=True)
        embed.add_field(name="起動時間 (Uptime)", value=uptime_str, inline=True)
        embed.add_field(name="総流通ポイント", value=f"{all_bal:,} pts", inline=False)
        embed.add_field(
            name="メンテナンスモード",
            value="🔴 ON" if self.bot.maintenance_mode else "🟢 OFF",
            inline=True,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @mod_group.command(name="status_all", description="全ユーザーの統計情報を一覧で表示します")
    @app_commands.default_permissions(administrator=True)
    async def status_all(self, interaction: discord.Interaction):
        all_stats = wallet.get_all_stats()
        if not all_stats:
            return await interaction.response.send_message("データがありません。", ephemeral=True)

        lines = []
        sorted_stats = sorted(all_stats.items(), key=lambda x: x[1].balance, reverse=True)
        for rank, (uid, data) in enumerate(sorted_stats, 1):
            user = interaction.guild.get_member(uid) if interaction.guild else None
            name = user.display_name if user else f"User({uid})"
            pts = data.balance
            wins = data.total_wins
            played = data.games_played
            max_win = data.max_win_amount
            lines.append(
                f"**{rank}位**: {name} | {pts:,} pts | {wins}勝/{played}戦 | Max: {max_win:,}"
            )

        embed = discord.Embed(
            title="🌐 エコシステム全体統計", description="\n".join(lines)[:4000], color=0x1ABC9C
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @mod_group.command(
        name="winner",
        description="殿堂入りプレイヤー（最多ポイント、最多勝利、最大一撃）を表彰します",
    )
    @app_commands.default_permissions(administrator=True)
    async def winner(self, interaction: discord.Interaction):
        all_stats = wallet.get_all_stats()
        if not all_stats:
            return await interaction.response.send_message("データがありません。", ephemeral=True)

        top_bal_id = max(all_stats.items(), key=lambda x: x[1].balance)[0]
        top_wins_id = max(all_stats.items(), key=lambda x: x[1].total_wins)[0]
        top_max_id = max(all_stats.items(), key=lambda x: x[1].max_win_amount)[0]

        def get_name(uid):
            user = interaction.guild.get_member(uid) if interaction.guild else None
            return user.display_name if user else f"User({uid})"

        embed = discord.Embed(
            title="🏆 Discord Economy Hall of Fame 🏆",
            description="現在までの最終結果を発表します！",
            color=0xF1C40F,
        )

        embed.add_field(
            name="💰 最多資産王",
            value=f"**{get_name(top_bal_id)}**\n({all_stats[top_bal_id].balance:,} pts)",
            inline=False,
        )
        embed.add_field(
            name="👑 最多勝利王",
            value=f"**{get_name(top_wins_id)}**\n({all_stats[top_wins_id].total_wins} 勝)",
            inline=False,
        )
        embed.add_field(
            name="💥 最大一撃王",
            value=f"**{get_name(top_max_id)}**\n({all_stats[top_max_id].max_win_amount:,} pts)",
            inline=False,
        )

        await interaction.response.send_message(embed=embed, ephemeral=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
