import discord


class PokerFormatter:
    """ポーカーのUI表示を整形するフォーマッタ"""

    @classmethod
    def format_error_embed(cls, message: str) -> discord.Embed:
        """カジノテーマのエラーEmbedを構築します。"""
        # Option A: Deep Green (0x1F8B4C) + Gold titles
        embed = discord.Embed(
            title="♣️ Poker Error ♦️",
            description=f"**{message}**",
            color=0x1F8B4C,  # ポーカーテーブルの緑
        )
        embed.set_footer(text="Casino Floor - Texas Hold'em")
        # トランプマークを装飾に使用
        # ♠️ ❤️ ♣️ ♦️
        return embed
