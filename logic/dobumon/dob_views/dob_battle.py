import asyncio
from typing import TYPE_CHECKING, Callable, Dict, List, Optional

import discord

if TYPE_CHECKING:
    from logic.dobumon.core.dob_manager import DobumonManager
    from logic.dobumon.core.dob_models import Dobumon

from core.utils.logger import Logger
from managers.manager import game_manager

from .dob_common import DobumonBaseView, DobumonSelect
from .dob_formatter import DobumonFormatter


class DobumonSelectionView(DobumonBaseView):
    """
    怒武者を選択してアクション（野生戦、決闘など）を開始するための汎用ビュー。
    """

    def __init__(
        self,
        user: discord.User,
        dobumons: List["Dobumon"],
        callback_func: Callable,
        title: str,
        description: str,
        button_label: str = "戦闘開始",
        button_style: discord.ButtonStyle = discord.ButtonStyle.success,
        color: int = 0x2ECC71,
        extra_callback_args: Optional[tuple] = None,
        public_interaction: Optional[discord.Interaction] = None,
        timeout: float = 120.0,
    ):
        super().__init__(user=user, timeout=timeout)
        self.dobumons = dobumons
        self.callback_func = callback_func
        self.title = title
        self.description = description
        self.color = color
        self.extra_callback_args = extra_callback_args or ()
        self.public_interaction = public_interaction
        self.selected_dobumon_id: Optional[str] = None

        self.dobumon_select = DobumonSelect(dobumons, "使用する怒武者を選択...")
        self.add_item(self.dobumon_select)

        # ボタンを動的に作成してプロパティを設定
        self.confirm_button.label = button_label
        self.confirm_button.style = button_style

    async def update_message(self, interaction: discord.Interaction):
        for option in self.dobumon_select.options:
            option.default = option.value == self.selected_dobumon_id

        self.confirm_button.disabled = not self.selected_dobumon_id
        embed = discord.Embed(
            title=self.title,
            description=self.description,
            color=self.color,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="確定", style=discord.ButtonStyle.success, disabled=True)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        button.disabled = True
        button.label = "準備中..."
        self.dobumon_select.disabled = True
        await interaction.response.edit_message(view=self)

        self.stop()

        # 実況に使用するインタラクションを決定（指定があればそれを使用、なければ現在のもの）
        display_interaction = self.public_interaction or interaction

        # コールバック実行 (interaction, *extra_args, selected_dobumon_id)
        await self.callback_func(
            display_interaction, *self.extra_callback_args, self.selected_dobumon_id
        )

    async def on_timeout(self):
        pass


class ChallengeView(DobumonBaseView):
    """
    決闘の受諾・拒否を行うためのインターフェース。
    """

    def __init__(
        self,
        attacker: "Dobumon",
        attacker_user: discord.User,
        target_user: discord.User,
        manager: "DobumonManager",
        callback_func: Callable,
        timeout: float = 60.0,
    ):
        super().__init__(user=target_user, timeout=timeout)
        self.attacker = attacker
        self.attacker_user = attacker_user
        self.target_user = target_user
        self.manager = manager
        self.callback_func = callback_func
        self.accepted: Optional[bool] = None
        self.initial_interaction: Optional[discord.Interaction] = None
        self.interaction: Optional[discord.Interaction] = None

    def _disable_all(self):
        for item in self.children:
            item.disabled = True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.target_user.id:
            await interaction.response.send_message(
                "⚠️ あなたはこの決闘の対象ではありません。", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="受諾", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):

        self.accepted = True
        self.interaction = interaction
        self._disable_all()
        await interaction.response.edit_message(view=self)
        self.stop()

        # 防衛側の怒武者を取得
        target_dobumons = self.manager.get_user_dobumons(self.target_user.id, only_alive=True)
        if not target_dobumons:
            return await interaction.followup.send(
                "❌ 有効な怒武者を所持していません。", ephemeral=True
            )

        if len(target_dobumons) == 1:
            # 1体のみの場合は即座にバトル開始
            await self.callback_func(
                interaction, self.attacker_user, self.attacker, target_dobumons[0].dobumon_id
            )
        else:
            # 2体以上の場合は選択メニューを表示
            view = DobumonSelectionView(
                user=self.target_user,
                dobumons=target_dobumons,
                callback_func=self.callback_func,
                title="⚔️ 防衛怒武者選択",
                description=f"**{self.attacker_user.display_name}** の **{self.attacker.name}** と戦わせる自分の怒武者を選んでください。",
                button_label="対戦開始",
                button_style=discord.ButtonStyle.danger,
                color=0xFF0000,
                extra_callback_args=(self.attacker_user, self.attacker),
                public_interaction=interaction,  # 受諾ボタンが押されたインタラクションを渡す
            )
            embed = discord.Embed(title=view.title, description=view.description, color=view.color)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="拒否", style=discord.ButtonStyle.secondary, emoji="🏳️")
    async def refuse(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.accepted = False
        self.interaction = interaction
        self._disable_all()

        embed = interaction.message.embeds[0]
        embed.title = "🕊️ 決闘拒否"
        embed.description = (
            f"**{interaction.user.display_name}** は決闘を拒否しました。命拾いしましたね。"
        )
        embed.color = discord.Color.light_grey()

        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    async def on_timeout(self):
        if self.initial_interaction:
            game_manager.end_session(self.initial_interaction.channel_id)
            try:
                embed = discord.Embed(
                    title="🕊️ 決闘中止",
                    description="対戦相手の応答がなかったため、決闘は中止されました。",
                    color=discord.Color.light_grey(),
                )
                await self.initial_interaction.edit_original_response(embed=embed, view=None)
            except:
                pass
            Logger.info(
                "Dobumon", f"Challenge timed out for channel {self.initial_interaction.channel_id}"
            )


class BattleAutoView(DobumonBaseView):
    def __init__(
        self,
        user: discord.User,
        dobu1: "Dobumon",
        dobu2: "Dobumon",
        steps: List[Dict],
        winner_id: Optional[str],
        loser_id: Optional[str],
        finish_callback: Callable,
        timeout: float = 600.0,
    ):
        super().__init__(user=user, timeout=timeout)
        self.dobu1 = dobu1
        self.dobu2 = dobu2
        self.steps = steps
        self.winner_id = winner_id
        self.loser_id = loser_id
        self.finish_callback = finish_callback
        self.channel_id: Optional[int] = None
        self.current_index = 0
        self.is_skipped = False
        self._battle_ended = False
        self._task: Optional[asyncio.Task] = None

    def get_attr_emoji(self, attr: str) -> str:
        return {"fire": "🔥", "water": "💧", "grass": "🌿"}.get(attr, "❓")

    def create_embed(self) -> discord.Embed:
        step = self.steps[self.current_index]
        p1_emoji = self.get_attr_emoji(self.dobu1.attribute)
        p2_emoji = self.get_attr_emoji(self.dobu2.attribute)

        embed = discord.Embed(title="⚔️ 決闘実況", color=0xFF0000)

        p1_bar = DobumonFormatter.get_hp_bar(step["p1_hp"], self.dobu1.hp, length=10, is_owner=True)
        p2_bar = DobumonFormatter.get_hp_bar(step["p2_hp"], self.dobu2.hp, length=10, is_owner=True)

        lines = [
            f"{p1_emoji} **{self.dobu1.name}**",
            f"`{p1_bar}`",
            "",
            f"{p2_emoji} **{self.dobu2.name}**",
            f"`{p2_bar}`",
            "━━━━━━━━━━━━━━━━━━━━",
        ]

        if step["turn"] == 0:
            lines.append(" 戦闘開始！")
        else:
            attacker = self.dobu1 if step["attacker"] == 1 else self.dobu2
            defender = self.dobu2 if step["attacker"] == 1 else self.dobu1

            action_name = step["action"]
            if not step["is_skill"]:
                suffix = " の攻撃！"
            else:
                suffix = f" のスキル「**{action_name}**」！"

            lines.append(f" ⚔️ **{attacker.name}** {suffix}")

            if not step.get("hit", True):
                lines.append(f" 💨 **{defender.name}** は回避した！")
            else:
                lines.append(f" 💥 **{defender.name}** に **{step['damage']}** ダメージ！")

        if self.current_index >= len(self.steps) - 1:
            lines.append("\n🏁 **戦闘終了**")

        embed.description = "\n".join(lines)
        return embed

    async def start(self, interaction: discord.Interaction):
        self.channel_id = interaction.channel_id
        self._task = asyncio.create_task(self._run_loop(interaction))

    async def _run_loop(self, interaction: discord.Interaction):
        while self.current_index < len(self.steps) - 1 and not self.is_skipped:
            await asyncio.sleep(1.0)
            if self.is_skipped:
                break
            self.current_index += 1

            try:
                await interaction.edit_original_response(
                    embed=self.create_embed(), view=self if not self._battle_ended else None
                )
            except:
                break

        if not self._battle_ended:
            self._battle_ended = True
            self.current_index = len(self.steps) - 1
            self._disable_all()
            try:
                await interaction.edit_original_response(embed=self.create_embed(), view=None)
            except:
                pass
            await self.finish_callback(interaction, self.winner_id, self.loser_id)
            self.stop()

    def _disable_all(self):
        for item in self.children:
            item.disabled = True

    @discord.ui.button(label="スキップ", style=discord.ButtonStyle.secondary, emoji="⏩")
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self._battle_ended:
            return

        self.is_skipped = True
        self._battle_ended = True
        self.current_index = len(self.steps) - 1
        self._disable_all()

        await interaction.response.edit_message(embed=self.create_embed(), view=None)
        await self.finish_callback(interaction, self.winner_id, self.loser_id)
        if self._task:
            self._task.cancel()
        self.stop()

    async def on_timeout(self):
        if self._battle_ended:
            return

        self._battle_ended = True
        if self.channel_id:
            game_manager.end_session(self.channel_id)
        Logger.info("Dobumon", f"Battle visualization timed out (Channel: {self.channel_id}).")
        if self._task:
            self._task.cancel()
