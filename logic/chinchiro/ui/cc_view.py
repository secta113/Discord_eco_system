import discord

from core.ui.view_base import BaseView
from core.utils.formatters import f_bold_pts
from logic.chinchiro.cc_service import ChinchiroService


class ChinchiroBaseView(BaseView):
    """チンチロリン関連の共通エラーハンドリングを備えた基底View"""

    pass


class ChinchiroView(ChinchiroBaseView):
    """チンチロリン専用のUIコンポーネント"""

    def __init__(self, session: ChinchiroService, cleanup_callback, save_callback=None):
        super().__init__(timeout=None)
        self.session = session
        self.cleanup_callback = cleanup_callback
        self.save_callback = save_callback

    @discord.ui.button(label="🎲 振る", style=discord.ButtonStyle.primary)
    async def roll_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # タイムアウト対策で即座に defer する
        await interaction.response.defer()

        # Service側で例外が投げられるため、手動チェックを削除
        dice, dice_str, role_name, strength, is_fixed, h_triggered = self.session.roll_action(
            interaction.user.id
        )

        if not is_fixed:
            if self.save_callback:
                self.save_callback()
            msg = f"🎲 {interaction.user.mention}: {dice_str} **【{role_name}】** (残:{3 - self.session.current_roll_count}回)"
            # 役が確定していない場合は、現在のメッセージを上書きする
            await interaction.edit_original_response(content=msg, view=self)
        else:
            # 役が確定した場合
            self.session.record_hand(interaction.user.id, dice, role_name, strength, h_triggered)
            msg = f"🎲 {interaction.user.mention}: {dice_str} **【{role_name}】** (確定)"

            # 現在のメッセージのボタンを無効化して上書き
            for child in self.children:
                child.disabled = True
            await interaction.edit_original_response(content=msg, view=self)

            if self.session.next_turn():
                if self.save_callback:
                    self.save_callback()

                # 次のプレイヤーの手番用にボタンを有効化して新しいメッセージを送信
                for child in self.children:
                    child.disabled = False
                next_p = self.session.get_current_player()
                await interaction.followup.send(
                    f"次は {next_p['mention']} です。🎲 振るボタンを押してください。", view=self
                )
            else:
                winner, sorted_scores, actual_payout = self.session.finalize()

                embed = discord.Embed(title="🏆 決着 🏆", color=0xF1C40F)
                if winner:
                    embed.description = f"**{winner['name']}** が配当 {f_bold_pts(actual_payout)} (システムボーナス含む) を総取りしました！"
                else:
                    embed.description = "全員役なしのため、ポットは没収されました。"

                rank_str = "\n".join([f"・**{s['name']}**: {s['text']}" for s in sorted_scores])
                embed.add_field(name="最終順位", value=rank_str, inline=False)

                # ゲーム終了なので新しいメッセージとしてEmbed(リザルト)を出す
                await interaction.followup.send(embed=embed)

                if self.cleanup_callback:
                    self.cleanup_callback()
