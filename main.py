import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from core.utils.config import VERSION
from core.utils.logger import Logger


class EconomyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

        # メンテナンスモードの状態をBotインスタンスに持たせる
        self.maintenance_mode = False

    async def setup_hook(self):
        """Cogの読み込みとコマンドの同期"""
        # アセットの事前読み込み (CPUブロッキング防止)
        from core.utils.card_assets import CardAssetManager
        from core.utils.font_manager import FontManager

        await CardAssetManager.preload()
        FontManager.preload()

        # Cogsの読み込み
        cogs = ["cogs.economy", "cogs.admin", "cogs.games", "cogs.system", "cogs.dobumon"]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                Logger.info("Main", f"Loaded extension: {cog}")
            except Exception as e:
                Logger.error("Main", f"Failed to load extension {cog}: {e}")

        # コマンドの同期
        guild_id = os.getenv("DISCORD_GUILD_ID")
        if guild_id:
            my_guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=my_guild)
            await self.tree.sync(guild=my_guild)
            Logger.info("Main", f">>> Commands synced to Guild: {guild_id}")
        else:
            await self.tree.sync()
            Logger.info("Main", ">>> Commands synced Globally")


def main():
    load_dotenv()

    # ターミナルへのログ出力設定（一時的デバッグ用）
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        Logger.error("Main", "DISCORD_BOT_TOKEN is not set in .env")
        return

    bot = EconomyBot()
    bot.run(token)


if __name__ == "__main__":
    main()
