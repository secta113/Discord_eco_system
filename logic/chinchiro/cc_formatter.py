import discord


class ChinchiroFormatter:
    """チンチロリンのUI表示を整形するフォーマッタ"""

    @classmethod
    def format_error_embed(cls, message: str) -> discord.Embed:
        """和風（藍色）テーマのエラーEmbedを構築します。"""
        embed = discord.Embed(
            title="🏮 チンチロリン 相談処 🏮",
            description=f"**{message}**",
            color=0x1A237E,  # 深い藍色（Indigo）
        )
        embed.set_footer(text="御免遊ばせ - Discord Economy System")
        return embed
