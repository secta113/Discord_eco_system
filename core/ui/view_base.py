import traceback
from typing import Callable, Optional, Type

import discord
from discord import ui

from core.utils.exceptions import BotError
from core.utils.logger import Logger


class ErrorHandlerMixin:
    """
    ViewやModalで共通利用するエラーハンドラーのMixinクラス。
    """

    _error_formatters: dict[Type[Exception], Callable[[str], discord.Embed]] = {}

    @classmethod
    def register_error_formatter(
        cls, exc_cls: Type[Exception], formatter_func: Callable[[str], discord.Embed]
    ):
        cls._error_formatters[exc_cls] = formatter_func

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, item: Optional[ui.Item] = None
    ) -> None:
        from discord.errors import NotFound

        orig_error = getattr(error, "original", error)

        # 1. Unknown interaction (10062) は無視
        if isinstance(orig_error, NotFound) and orig_error.code == 10062:
            return

        # 2. BotError (ユーザー向けエラー) の処理
        if isinstance(orig_error, BotError):
            embed = None

            # レジストリから適切なフォーマッターを探す (継承関係も考慮)
            for exc_cls, formatter in self._error_formatters.items():
                if isinstance(orig_error, exc_cls):
                    embed = formatter(orig_error.message)
                    break

            if not embed:
                # デフォルトのEmbed
                embed = discord.Embed(
                    title="⚠️ Notice", description=orig_error.message, color=0xF1C40F
                )

            await self._safe_send_error(interaction, embed=embed)
            return

        # 3. 予期せぬエラーのログ出力と通知
        Logger.error("UI", f"Unexpected error in {self.__class__.__name__}: {error}")
        traceback.print_exc()

        msg = "⚠️ 予期せぬエラーが発生しました。時間を置いて再度お試しください。"
        await self._safe_send_error(interaction, content=msg)

    async def _safe_send_error(
        self,
        interaction: discord.Interaction,
        content: Optional[str] = None,
        embed: Optional[discord.Embed] = None,
    ):
        """インタラクションの状態に合わせて安全にエラーメッセージを送信する"""
        try:
            if interaction.response.is_done():
                await interaction.followup.send(content=content, embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(
                    content=content, embed=embed, ephemeral=True
                )
        except Exception as e:
            Logger.error("UI", f"Failed to send error message: {e}")


class BaseView(ErrorHandlerMixin, ui.View):
    """
    システム全体のViewの基底クラス。
    Unknown interaction (10062) の抑制と、レジストリベースの統一されたエラーハンドリングを提供します。
    """

    pass


class BaseModal(ErrorHandlerMixin, ui.Modal):
    """
    システム全体のModalの基底クラス。
    Viewと同様のエラーハンドリングを提供します。
    """

    pass


class JoinView(BaseView):
    """
    ゲーム参加募集用の共通View。
    """

    def __init__(self, channel_id: int, manager, show_start: bool = True):
        super().__init__(timeout=None)
        self.channel_id = channel_id
        self.manager = manager

        if not show_start:
            start_buttons = [c for c in self.children if getattr(c, "label", "") == "▶️ 開始する"]
            for b in start_buttons:
                self.remove_item(b)

    @ui.button(label="✋ 参加する", style=discord.ButtonStyle.success)
    async def join_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()

        if getattr(interaction.client, "maintenance_mode", False):
            return await interaction.followup.send(
                "🛠️ 現在メンテナンス中のため、参加できません。", ephemeral=True
            )

        try:
            message = self.manager.join_session(self.channel_id, interaction.user)
            await interaction.followup.send(message, ephemeral=False)
        except Exception as e:
            raise e

    @ui.button(label="▶️ 開始する", style=discord.ButtonStyle.primary)
    async def start_button(self, interaction: discord.Interaction, button: ui.Button):
        from . import starter

        await interaction.response.defer()

        session = self.manager.get_session(self.channel_id)
        if not session:
            return await interaction.followup.send(
                "⚠️ 開始可能なゲームセッションがありません。", ephemeral=True
            )
        if session.players[0]["id"] != interaction.user.id:
            return await interaction.followup.send("❌ ホストのみが開始できます。", ephemeral=True)

        session.can_start()

        for child in self.children:
            child.disabled = True

        try:
            if not interaction.response.is_done():
                await interaction.response.edit_message(view=self)
            else:
                await interaction.edit_original_response(view=self)
        except Exception:
            pass

        await starter.execute_game_start(interaction, session)

    @ui.button(label="🛑 キャンセル", style=discord.ButtonStyle.danger)
    async def cancel_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()

        session = self.manager.get_session(self.channel_id)
        if not session:
            return await interaction.followup.send(
                "⚠️ キャンセル可能なゲームセッションがありません。", ephemeral=True
            )

        host_id = getattr(session, "host_id", None)
        if host_id is None and session.players:
            host_id = session.players[0]["id"]

        if host_id != interaction.user.id and not getattr(
            interaction.user.guild_permissions, "administrator", False
        ):
            return await interaction.followup.send(
                "❌ ホストのみがキャンセルできます。", ephemeral=True
            )

        if hasattr(session, "cancel"):
            session.cancel()
        elif hasattr(session, "refund_all"):
            session.refund_all()

        self.manager.end_session(self.channel_id)

        for child in self.children:
            child.disabled = True

        embed = discord.Embed(
            title="🛑 募集キャンセル",
            description="募集がキャンセルされ、全額返金されました。",
            color=0x95A5A6,
        )
        try:
            await interaction.edit_original_response(content=None, embed=embed, view=self)
        except Exception:
            pass
