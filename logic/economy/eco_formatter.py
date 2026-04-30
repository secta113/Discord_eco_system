import discord


class EconomyFormatter:
    """エコノミー関連のUI表示を整形するフォーマッタ"""

    @classmethod
    def format_error_embed(cls, message: str) -> discord.Embed:
        """「黄金（Gold）」テーマのエラーEmbedを構築します。"""
        embed = discord.Embed(
            title="💰 Economy Notice",
            description=f"**{message}**",
            color=0xF1C40F,  # ゴールド（明るい黄色）
        )
        embed.set_footer(text="資産管理は計画的に - Discord Economy System")
        return embed
