import discord
from discord import app_commands
from discord.ext import commands

from core.utils.config import VERSION
from core.utils.exceptions import BotError, EconomyError
from core.utils.logger import Logger
from logic.blackjack.bj_exceptions import BlackjackError
from logic.blackjack.bj_formatter import BlackjackFormatter
from logic.chinchiro.cc_exceptions import ChinchiroError
from logic.chinchiro.cc_formatter import ChinchiroFormatter
from logic.dobumon.core.dob_exceptions import DobumonError
from logic.dobumon.dob_views import DobumonFormatter
from logic.economy.eco_formatter import EconomyFormatter
from logic.poker.pk_exceptions import PokerError
from logic.poker.pk_formatter import PokerFormatter


class System(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Context Menuの登録
        self.ctx_menu = app_commands.ContextMenu(
            name="User ID",
            callback=self.get_user_id,
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    @commands.Cog.listener()
    async def on_ready(self):
        Logger.info("Main", f">>> Discord Economy System {VERSION} Online as {self.bot.user}")

    async def get_user_id(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{member.display_name} のID: `{member.id}`", ephemeral=True
        )


async def setup(bot: commands.Bot):
    cog = System(bot)
    await bot.add_cog(cog)

    # グローバルエラーハンドラの設定
    @bot.tree.error
    async def on_app_command_error(
        interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        """スラッシュコマンドのグローバルエラーハンドラ"""
        # 実行中に発生した例外の取り出し
        orig_error = getattr(error, "original", error)

        if isinstance(orig_error, BotError):
            # ユーザー向けに定義されたエラー
            if isinstance(orig_error, DobumonError):
                # 怒武者専用フォーマット
                embed = DobumonFormatter.format_error_embed(orig_error.message)
                if not interaction.response.is_done():
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.followup.send(embed=embed, ephemeral=True)
            elif isinstance(orig_error, PokerError):
                # ポーカー専用フォーマット
                embed = PokerFormatter.format_error_embed(orig_error.message)
                if not interaction.response.is_done():
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.followup.send(embed=embed, ephemeral=True)
            elif isinstance(orig_error, ChinchiroError):
                # チンチロリン専用フォーマット
                embed = ChinchiroFormatter.format_error_embed(orig_error.message)
                if not interaction.response.is_done():
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.followup.send(embed=embed, ephemeral=True)
            elif isinstance(orig_error, BlackjackError):
                # ブラックジャック専用フォーマット
                embed = BlackjackFormatter.format_error_embed(orig_error.message)
                if not interaction.response.is_done():
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.followup.send(embed=embed, ephemeral=True)
            elif isinstance(orig_error, EconomyError):
                # エコノミー（経済）専用フォーマット
                embed = EconomyFormatter.format_error_embed(orig_error.message)
                if not interaction.response.is_done():
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                # 一般的なエラー表示
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        f"⚠️ {orig_error.message}", ephemeral=True
                    )
                else:
                    await interaction.followup.send(f"⚠️ {orig_error.message}", ephemeral=True)
            return

        # 予期せぬエラー
        # Unknown interaction (10062) は無視（タイムアウト等で既に無効な場合）
        if hasattr(orig_error, "code") and orig_error.code == 10062:
            Logger.warn("Main", "Interaction timed out or already handled (10062).")
            return

        Logger.error("Main", f"!!! Unexpected Error: {error}")
        import traceback

        traceback.print_exc()

        msg = "予期せぬエラーが発生しました。時間を置いて再度お試しください。"
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ {msg}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ {msg}", ephemeral=True)
        except Exception as e:
            Logger.error("Main", f"Failed to send error message: {e}")
