from functools import wraps
from typing import Callable

import discord
from discord import app_commands

from core.utils.exceptions import MaintenanceError


def defer_response(ephemeral: bool = False):
    """レスポンスを defer するデコレータ (Unknown Interaction 対策)"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # args[0] が self, args[1] が interaction
            interaction = args[1] if len(args) > 1 else args[0]
            if isinstance(interaction, discord.Interaction):
                if not interaction.response.is_done():
                    await interaction.response.defer(ephemeral=ephemeral)
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def check_maintenance():
    """メンテナンスモード中かどうかをチェックするデコレータ"""

    def predicate(interaction: discord.Interaction) -> bool:
        # bot instance (interaction.client) に保持するように変更
        if getattr(interaction.client, "maintenance_mode", False):
            raise MaintenanceError("現在メンテナンス中です。しばらくお待ちください。")
        return True

    return app_commands.check(predicate)
