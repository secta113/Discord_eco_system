import discord
from discord import app_commands
from discord.ext import commands

from core.economy import wallet
from core.ui.view_base import BaseView, JoinView
from core.utils.decorators import check_maintenance, defer_response
from core.utils.exceptions import EconomyError
from core.utils.formatters import f_bold_pts, f_pts
from logic.bet_service import BetService
from logic.blackjack.bj_exceptions import BlackjackError
from logic.blackjack.bj_formatter import BlackjackFormatter
from logic.chinchiro.cc_exceptions import ChinchiroError
from logic.chinchiro.cc_formatter import ChinchiroFormatter
from logic.economy.eco_formatter import EconomyFormatter
from logic.gacha_service import gacha_service
from logic.match.ui.match_view import MatchJoinView
from logic.poker.pk_exceptions import PokerError
from logic.poker.pk_formatter import PokerFormatter
from managers.manager import game_manager


class Games(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # エラーフォーマッターの登録
        BaseView.register_error_formatter(BlackjackError, BlackjackFormatter.format_error_embed)
        BaseView.register_error_formatter(ChinchiroError, ChinchiroFormatter.format_error_embed)
        BaseView.register_error_formatter(PokerError, PokerFormatter.format_error_embed)
        BaseView.register_error_formatter(EconomyError, EconomyFormatter.format_error_embed)

    game_group = app_commands.Group(name="dd-game", description="ゲーム募集用コマンド群")

    @game_group.command(name="blackjack", description="ブラックジャックの募集を開始します")
    @app_commands.describe(bet="参加に必要なポイント")
    @check_maintenance()
    @defer_response(ephemeral=False)
    async def blackjack(self, interaction: discord.Interaction, bet: int = 100):
        session, msg = game_manager.create_blackjack(interaction.channel_id, interaction.user, bet)
        if not session:
            return await interaction.followup.send(msg, ephemeral=True)
        embed = discord.Embed(title="🃏 ブラックジャック 参加者募集", color=0x9B59B6)
        embed.add_field(name="ホスト", value=interaction.user.mention)
        embed.add_field(name="参加コスト", value=f_pts(bet))
        embed.description = "Botディーラーと勝負！\n下の「参加する」ボタンで参加し、準備ができたらホストが開始ボタンを押してください。"
        view = JoinView(interaction.channel_id, game_manager)
        await interaction.followup.send(embed=embed, view=view)

    @game_group.command(name="chinchiro", description="チンチロリンの募集を開始します")
    @app_commands.describe(bet="参加に必要なポイント")
    @check_maintenance()
    @defer_response(ephemeral=False)
    async def chinchiro(self, interaction: discord.Interaction, bet: int = 100):
        session, msg = game_manager.create_chinchiro(interaction.channel_id, interaction.user, bet)
        if not session:
            return await interaction.followup.send(msg, ephemeral=True)
        embed = discord.Embed(title="🎲 チンチロリン 参加者募集 🎲", color=0x3498DB)
        embed.add_field(name="ホスト", value=interaction.user.mention)
        embed.add_field(name="参加コスト", value=f_pts(bet))
        embed.set_footer(
            text="下の参加ボタンで参加し、全員揃ったらホストが開始ボタンを押してください。"
        )
        view = JoinView(interaction.channel_id, game_manager)
        await interaction.followup.send(embed=embed, view=view)

    @game_group.command(name="match", description="外部対戦（エスクロー）の募集を開始します")
    @app_commands.describe(bet="参加に必要なポイント")
    @check_maintenance()
    @defer_response(ephemeral=False)
    async def match(self, interaction: discord.Interaction, bet: int):
        session, msg = game_manager.create_match(interaction.channel_id, interaction.user, bet)
        if not session:
            return await interaction.followup.send(msg, ephemeral=True)
        embed = discord.Embed(title="⚔️ 外部マッチ 募集", color=0xE74C3C)
        embed.add_field(name="ホスト", value=interaction.user.mention)
        embed.add_field(name="参加コスト", value=f_pts(bet))
        embed.description = (
            "下の「参加する」で参加。終了後、ホストは「🏁 結果報告」ボタンを押してください。"
        )
        view = MatchJoinView(interaction.channel_id, game_manager)
        await interaction.followup.send(embed=embed, view=view)

    @game_group.command(name="poker", description="テキサス・ホールデムの募集を開始します")
    @app_commands.describe(
        bet="ベースとなる参加ポイント (これがBBとなり、SBはその半額になります)",
        buyin="参加時に預けるスタック(持ち点)。省略時はBBの20倍（ショートバイイン対応）",
        players="目標人数 (2〜6)。不足分はNPCで補完されます (デフォルト: 6)",
    )
    @check_maintenance()
    @defer_response(ephemeral=False)
    async def poker(
        self, interaction: discord.Interaction, bet: int = 100, buyin: int = None, players: int = 4
    ):
        session, msg = game_manager.create_poker(
            interaction.channel_id, interaction.user, bet, buyin, players
        )
        if not session:
            return await interaction.followup.send(msg, ephemeral=True)

        actual_buyin = buyin if buyin is not None else bet * 20
        embed = discord.Embed(title="♣️ テキサス・ホールデム 参加者募集", color=0x1F8B4C)
        embed.add_field(name="ホスト", value=interaction.user.mention)
        embed.add_field(name="SB", value=f_pts(max(1, bet // 2)))
        embed.add_field(name="BB", value=f_pts(bet))
        embed.add_field(name="上限スタック (参加費)", value=f_pts(actual_buyin))
        embed.description = (
            "本格的なテキサス・ホールデム対人戦！\n「参加する」でエントリーし、ホストが開始ボタンを押してください。\n"
            "※ポットから **5%の手数料(Rake)** が徴収されます。\n"
            "※残高が上限スタック未満の場合は「全財産」がスタックとなります（ショートバイイン）。\n"
            "※自分の手札は開始後「手札を確認」ボタンで個別確認できます。"
        )
        view = JoinView(interaction.channel_id, game_manager)
        await interaction.followup.send(embed=embed, view=view)

    @game_group.command(
        name="poker_rule", description="テキサス・ホールデムのルールと操作方法を確認します"
    )
    @defer_response(ephemeral=True)
    async def poker_rule(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="♣️ Texas Hold'em Poker - 究極ガイド",
            color=0x1F8B4C,
            description=("2枚の手札と5枚の共通カードを組み合わせて、最強の5枚を作るポーカーです。"),
        )

        embed.add_field(
            name="🕹️ 操作ボタン解説",
            value=(
                "・**Check / Call**: 同額を維持してパス、または相手の賭け金に合わせます。\n"
                "・**Raise**: 賭け金を上乗せします。入力は「合計額」で行ってください。\n"
                "・**Fold**: このラウンドを降ります。賭けたチップは失われます。\n"
                "・**All-In**: 手持ちの全スタックを中央へ！勝負の瀬戸際です。\n"
                "・**手札を確認**: 自分だけに手札（ ephemeral ）を表示します。"
            ),
            inline=False,
        )

        embed.add_field(
            name="💰 ブラインドとスタック",
            value=(
                "・**BB (Big Blind)**: 募集時の `bet` 設定額。強制ベットの基準。\n"
                "・**SB (Small Blind)**: BBの半額。ボタンの次が支払い。\n"
                "・**スタック**: テーブル上のチップ。募集時の `buyin` (デフォルト20BB) が上限。\n"
                "※残高不足でも「全財産」で参加可能です（ショートバイイン）。"
            ),
            inline=False,
        )

        embed.add_field(
            name="🏁 ゲームの進行",
            value=". **プリフロップ** (手札2枚)\n2. **フロップ** (共通3枚)\n3. **ターン** (共通+1枚)\n4. **リバー** (共通+1枚)\n5. **ショウダウン** (手札公開！勝者がPotを総取り)",
            inline=False,
        )

        embed.add_field(
            name="🏆 役の強さ (強い順)",
            value=(
                "```\n"
                "1. ロイヤルフラッシュ (A-K-Q-J-10 同スート)\n"
                "2. ストレートフラッシュ (連続5枚 同スート)\n"
                "3. フォーカード (同じ数字4枚)\n"
                "4. フルハウス (3枚+2枚)\n"
                "5. フラッシュ (同スート5枚)\n"
                "6. ストレート (連続5枚)\n"
                "7. スリーカード (同じ数字3枚)\n"
                "8. ツーペア / ワンペア / ハイカード\n"
                "```"
            ),
            inline=False,
        )

        embed.add_field(
            name="🎰 ジャックポット (Jackpot)",
            value=("役に応じてJPから放出！\n・Royal: 100% / St-Flush: 50% / Quads: 10%"),
            inline=False,
        )

        embed.set_footer(text="Good Luck! | 詳細: /docs/poker.md")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @game_group.command(
        name="gacha",
        description="1日最大3回引けるデイリーガチャ (初回500pts〜 / 初回のみ未所持確定！)",
    )
    @check_maintenance()
    @defer_response(ephemeral=False)
    async def gacha(self, interaction: discord.Interaction):
        """1日最大3回限定のデイリーガチャ"""
        result = gacha_service.execute_gacha(interaction.user.id)

        event = result["event"]
        payout = result["payout"]
        cost = result["cost"]
        is_new = result["is_new"]
        is_guaranteed = result["is_guaranteed_new"]
        count = result["count_today"]

        rarity_colors = {
            "Ultimate": 0xFFFFFF,
            "Legendary": 0xFFD700,
            "Epic": 0x9B59B6,
            "Rare": 0x3498DB,
            "Normal": 0x2ECC71,
            "Bad": 0xE67E22,
            "Disaster": 0xE74C3C,
        }

        # 称号やステータス表示
        title_prefix = "✨ "
        if is_new:
            title_prefix = "🌟 【NEW!】 "

        guaranteed_text = " (新規確定枠)" if is_guaranteed else ""

        embed = discord.Embed(
            title=f"{title_prefix}ガチャ結果: 【{event['rarity']}】{guaranteed_text}",
            description=f"『{event['text']}』",
            color=rarity_colors.get(event["rarity"], 0x95A5A6),
        )

        embed.add_field(name="💰 獲得ポイント", value=f_bold_pts(payout), inline=True)
        embed.add_field(name="💸 使用コスト", value=f_pts(cost), inline=True)
        embed.add_field(
            name="💳 残高", value=f_pts(wallet.load_balance(interaction.user.id)), inline=True
        )

        collected, total, percentage = gacha_service.get_completion_info(interaction.user.id)
        footer_text = f"現在の図鑑コンプリート率: {collected}/{total} ({percentage:.1f}%)"
        if count < 3:
            footer_text += f" | 本日の残り: {3 - count}回"
        else:
            footer_text += " | 本日は終了です"

        embed.set_footer(text=footer_text)

        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="dd-cancel", description="【ホストのみ】現在募集中のゲームをキャンセルします"
    )
    @app_commands.describe(
        force="【ホスト/管理者用】既に開始して進行中のゲームでも強制終了して破棄します"
    )
    async def cancel_game_unified(self, interaction: discord.Interaction, force: bool = False):
        session = game_manager.get_session(interaction.channel_id)
        if not session:
            return await interaction.response.send_message(
                "⚠️ キャンセル可能なゲームセッションがありません。", ephemeral=True
            )

        is_recruiting = getattr(session, "status", "") == "recruiting"
        if not is_recruiting and not force:
            return await interaction.response.send_message(
                "⚠️ 既にゲームが開始されているため通常のキャンセルはできません。（強制終了するには force を True にしてください）",
                ephemeral=True,
            )

        host_id = getattr(session, "host_id", None)
        if host_id is None and session.players:
            host_id = session.players[0]["id"]

        if host_id != interaction.user.id and not getattr(
            interaction.user.guild_permissions, "administrator", False
        ):
            return await interaction.response.send_message(
                "❌ ホストまたは管理者のみがキャンセルできます。", ephemeral=True
            )

        if hasattr(session, "cancel"):
            session.cancel()
        elif hasattr(session, "refund_all"):
            session.refund_all()

        game_manager.end_session(interaction.channel_id)

        if force and not is_recruiting:
            await interaction.response.send_message(
                "⚠️ 進行中のゲームセッションを強制終了しました。（進行中に個別に消費されたポイントは返金されません）"
            )
        else:
            await interaction.response.send_message(
                "✅ ゲームの募集をキャンセルし、参加者に対してエスクローの返金処理を行いました。"
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Games(bot))
