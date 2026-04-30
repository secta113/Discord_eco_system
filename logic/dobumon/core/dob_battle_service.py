from typing import Optional

import discord

from core.economy import wallet
from core.utils.logger import Logger
from core.utils.time_utils import get_jst_today
from logic.dobumon.core.dob_exceptions import (
    DobumonError,
    DobumonExecutionError,
    DobumonNotFoundError,
)
from logic.dobumon.core.dob_manager import DobumonManager
from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.dob_battle.dob_engine import BattleEngine
from logic.dobumon.dob_views import (
    DobumonFormatter,
)
from logic.dobumon.dob_views.dob_battle import (
    BattleAutoView,
    ChallengeView,
    DobumonSelectionView,
)
from managers.manager import game_manager


class DobumonBattleService:
    """
    怒武者の戦闘（野生戦、決闘）の実行ロジックを管理するサービス。
    """

    def __init__(self, manager: DobumonManager):
        self.manager = manager

    async def execute_wild_battle(self, interaction: discord.Interaction):
        """野生戦ウィザード（ドブモン選択→ランク選択→マップ選択）を起動します"""
        user_id = interaction.user.id
        dobumons = self.manager.get_user_dobumons(user_id, only_alive=True)
        if not dobumons:
            raise DobumonNotFoundError("参加可能な怒武者がいません。")

        # 1. プレイヤーの上限チェック (1日5回)
        MAX_WILD_LIMIT = 5
        today_str = get_jst_today()
        user_battle_count = wallet.get_wild_battle_count(user_id)
        user_last_date = wallet.get_last_wild_battle_date(user_id)

        if user_last_date != today_str:
            wallet.set_last_wild_battle_date(user_id, today_str)
            wallet.set_wild_battle_count(user_id, 0)
            user_battle_count = 0

        if user_battle_count >= MAX_WILD_LIMIT:
            raise DobumonError("もう近くの野生はすでにドブになった")

        from logic.dobumon.dob_battle.wild import WildBattleWizard

        view = WildBattleWizard(interaction.user, dobumons, self.start_wild_battle)
        embed = view.create_embed()

        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def start_wild_battle(
        self, interaction: discord.Interaction, my_dobumon_id: str, rank_key: str, map_id: str
    ):
        """ウィザード完了後、実際のバトルを開始します"""
        user_id = interaction.user.id
        attacker = self.manager.get_dobumon(my_dobumon_id)
        if not attacker or attacker.owner_id != str(user_id) or not attacker.is_alive:
            raise DobumonNotFoundError("有効な自分の怒武者が見つかりません。")

        # 設定の取得
        from logic.dobumon.dob_battle.wild import WildBattleConfig

        rank_info = WildBattleConfig.get_rank(rank_key)
        map_info = WildBattleConfig.get_map(rank_key, map_id)

        # 野生個体の生成
        from logic.dobumon.core.dob_factory import DobumonFactory

        wild_dobu = DobumonFactory.create_wild(
            stats_config=rank_info["stats"],
            attribute=map_info["attribute"],
            forbidden_depth=rank_info.get("forbidden_depth", 0),
        )

        engine = BattleEngine(attacker, wild_dobu)
        result = engine.simulate()

        # 実況Viewを作成
        battle_view = BattleAutoView(
            interaction.user,
            attacker,
            wild_dobu,
            result["steps"],
            result["winner_id"],
            result["loser_id"],
            self._finish_wild_battle_factory(user_id, attacker, wild_dobu, result, rank_key),
        )

        # 最初の表示（野生出現 + バトル開始）
        embed = battle_view.create_embed()
        embed.title = f"🌳 {map_info['name']} にて野生出現！ vs {attacker.name}"
        embed.set_footer(text=f"難易度: {rank_info['name']}")

        await interaction.response.edit_message(embed=embed, view=battle_view)
        await battle_view.start(interaction)

    def _finish_wild_battle_factory(self, user_id, attacker, wild_dobu, result, rank_key: str):
        """野生戦終了時の処理を生成するクロージャ"""

        async def finish_wild_battle(inter: discord.Interaction, winner_id: str, _loser_id: str):
            game_manager.end_session(inter.channel_id)
            attacker.today_wild_battle_count += 1

            settlement = self.manager.settle_wild_battle(
                winner_id, attacker.dobumon_id, wild_dobu, rank_key=rank_key, battle_result=result
            )
            attr_emoji = {"fire": "🔥", "water": "💧", "grass": "🌿"}.get(attacker.attribute, "⚔️")

            if settlement["winner"] == "player":
                # プレイヤーの勝利数をインクリメント (5勝制限)
                curr_count = wallet.get_wild_battle_count(user_id)
                wallet.set_wild_battle_count(user_id, curr_count + 1)

                reward = settlement["reward"]
                curr = wallet.load_balance(user_id)
                wallet.save_balance(user_id, curr + reward)
                wallet.add_history(user_id, f"野生戦勝利報酬 ({wild_dobu.name})", reward)
                new_win_count = attacker.win_count
                if new_win_count == 1:
                    flavor = "初陣を飾った。この勝利が, 伝説の幕開けとなるだろう。"
                elif new_win_count < 5:
                    flavor = "荒野を制した。その咆哮が, 野獣どもの心に恐怖を刻む。"
                elif new_win_count < 10:
                    flavor = "百戦錬磨の闘士よ。野生の獣など、もはや敵ではない。"
                else:
                    flavor = "修羅の頂に立つ者。その名を語るだけで、野生は震える。"
                bonus_text = (
                    " (属性不利ボーナス適用！)" if settlement.get("is_disadvantage_bonus") else ""
                )
                embed = discord.Embed(
                    title="🏆 勝利！",
                    description=(
                        f"{attr_emoji} **{attacker.name}** が **{wild_dobu.name}** を打ち倒した！\n*{flavor}*\n\n"
                        f"💰 **勝利報酬:** {reward:,} pts{bonus_text}\n"
                        f"🏅 **通算勝利数:** {new_win_count} 勝"
                    ),
                    color=0xF1C40F,
                )
                gains = settlement.get("gains")
                if gains:
                    gain_text = ", ".join([f"{k.upper()} +{v}" for k, v in gains.items()])
                    embed.add_field(
                        name="✨ 経験値獲得",
                        value=f"能力が向上しました！\n`{gain_text}`",
                        inline=False,
                    )
            else:
                death_msg = (
                    "\n⚠️ **" + attacker.name + " はドブになった。**"
                    if not attacker.is_alive
                    else "\n🩸 **"
                    + attacker.name
                    + " は致命傷を負ったが、辛うじて一命を取り留めた。**"
                )
                embed = discord.Embed(
                    title="💀 敗北...",
                    description=(
                        f"{attr_emoji} **{attacker.name}** は **{wild_dobu.name}** に敗れた。\n{death_msg}"
                    ),
                    color=0x2C3E50,
                )
            embed.set_footer(text="🍃 野生戦終了")
            try:
                await inter.edit_original_response(embed=embed, view=None)
            except:
                pass

        return finish_wild_battle

    async def execute_challenge(self, interaction: discord.Interaction, target: discord.Member):
        """決闘の挑戦申し込みフェーズ（ウィザード起動）"""
        user_id = interaction.user.id
        if target.id == user_id:
            raise DobumonError("自分自身には挑戦できません。")

        dobumons = self.manager.get_user_dobumons(user_id, only_alive=True)
        if not dobumons:
            raise DobumonNotFoundError("決闘に出せる怒武者を所持していません。")

        view = DobumonSelectionView(
            user=interaction.user,
            dobumons=dobumons,
            callback_func=self.start_challenge_wizard,
            title="⚔️ 決闘ウィザード",
            description=f"**{target.display_name}** にぶつける自分の怒武者を選んでください。\n敗北するとドブになるリスクがあります。",
            button_label="決闘を申し込む",
            button_style=discord.ButtonStyle.danger,
            color=0xFF0000,
            extra_callback_args=(target,),
            public_interaction=interaction,
        )
        embed = discord.Embed(title=view.title, description=view.description, color=view.color)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def start_challenge_wizard(
        self, interaction: discord.Interaction, target: discord.Member, attacker_dobumon_id: str
    ):
        """決闘の挑戦申し込み（受諾待ちビューの表示）"""
        user_id = interaction.user.id
        attacker = self.manager.get_dobumon(attacker_dobumon_id)
        if not attacker or not attacker.is_alive:
            raise DobumonNotFoundError("有効な自分の怒武者が見つかりません。")

        target_dobumons = self.manager.get_user_dobumons(target.id, only_alive=True)
        if not target_dobumons:
            raise DobumonError(
                f"**{target.display_name}** は現在、対戦可能な怒武者を所持していません。"
            )

        view = ChallengeView(
            attacker, interaction.user, target, self.manager, self.start_challenge_battle
        )
        view.initial_interaction = interaction

        embed = discord.Embed(
            title="⚔️ 決闘の申し込み",
            description=(
                f"**{interaction.user.display_name}** の **{attacker.name}** が、\n"
                f"**{target.display_name}** に決闘を申し込みました！\n\n"
                "敗北した怒武者や寿命を使い果たした怒武者は**ドブ**になります。"
            ),
            color=0xFF0000,
        )
        embed.set_footer(text="60秒以内に受諾してください。")

        await interaction.followup.send(content=target.mention, embed=embed, view=view)

    async def start_challenge_battle(
        self,
        interaction: discord.Interaction,
        attacker_user: discord.User,
        attacker: Dobumon,
        defender_id: str,
    ):
        """決闘の開始と実行（受諾および個体確定後）"""
        defender = self.manager.get_dobumon(defender_id)
        if not defender or not defender.is_alive:
            raise DobumonNotFoundError("防衛側の怒武者が存在しないか、既に生存していません。")

        engine = BattleEngine(attacker, defender)
        result = engine.simulate()

        session, msg = game_manager.create_dobumon_battle(
            interaction.channel_id,
            attacker_user,
            attacker,
            defender,
            result["steps"],
            result["winner_id"],
            result["loser_id"],
            battle_type="challenge",
        )

        if not session:
            raise DobumonExecutionError(f"対戦セッションの作成に失敗しました: {msg}")

        async def finish_pvp_battle(inter: discord.Interaction, winner_id: str, loser_id: str):
            game_manager.end_session(inter.channel_id)
            for combatant in [attacker, defender]:
                consumption_mod = combatant.consumption_mod

                combatant.lifespan = max(0.0, combatant.lifespan - (2.0 * consumption_mod))
                if combatant.lifespan <= 0:
                    self.manager.handle_death(combatant, "Lifespan Exhaustion in PvP Battle")

            settlement = self.manager.settle_battle(winner_id, loser_id, battle_result=result)
            winner_owner_id = int(settlement["winner_owner_id"])
            reward = settlement["reward"]

            curr = wallet.load_balance(winner_owner_id)
            wallet.save_balance(winner_owner_id, curr + reward)
            wallet.add_history(
                winner_owner_id, f"決闘勝利報酬 ({settlement['loser_name']}に勝利)", reward
            )

            winner_owner_name = settlement["winner_name"]
            if inter.guild:
                try:
                    m = await inter.guild.fetch_member(winner_owner_id)
                    winner_owner_name = m.display_name
                except:
                    pass

            loser_name = settlement["loser_name"]
            dead_dobu = next((c for c in [attacker, defender] if c.name == loser_name), None)
            death_msg = ""
            if dead_dobu:
                if not dead_dobu.is_alive:
                    death_msg = f"\n💀 **{loser_name}** はドブになった。"
                else:
                    death_msg = f"\n🩹 **{loser_name}** は大きな傷を負ったが、生存している。"

            embed = discord.Embed(
                title="🏆 決闘終結",
                description=(
                    f"激闘の末、**{settlement['winner_name']}** が勝利を収めた！\n\n"
                    f"💰 **勝利報酬:** {reward:,} pts が **{winner_owner_name}** に支払われました。"
                    f"{death_msg}"
                ),
                color=0xF1C40F,
            )
            try:
                await inter.edit_original_response(embed=embed, view=None)
            except:
                pass

        battle_view = BattleAutoView(
            interaction.user,
            attacker,
            defender,
            result["steps"],
            result["winner_id"],
            result["loser_id"],
            finish_pvp_battle,
        )

        if interaction.response.is_done():
            await interaction.edit_original_response(
                embed=battle_view.create_embed(), view=battle_view
            )
        else:
            await interaction.response.send_message(
                embed=battle_view.create_embed(), view=battle_view
            )
        await battle_view.start(interaction)
