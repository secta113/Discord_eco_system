import discord


class BlackjackFormatter:
    """ブラックジャックのUI表示を整形するフォーマッタ"""

    @classmethod
    def format_error_embed(cls, message: str) -> discord.Embed:
        """ラグジュアリー（紫＆金）テーマのエラーEmbedを構築します。"""
        embed = discord.Embed(
            title="✨ Blackjack VIP Lounge ✨",
            description=f"**{message}**",
            color=0x7B2CBF,  # ラグジュアリー・パープル
        )
        embed.set_footer(text="紳士淑女の嗜み - Discord Economy System")
        return embed
