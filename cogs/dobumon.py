import datetime
import traceback

import discord
from discord import app_commands
from discord.ext import commands, tasks

from core.economy import wallet
from core.handlers.storage import SQLiteDobumonRepository
from core.ui.view_base import BaseView
from core.utils.decorators import check_maintenance, defer_response
from core.utils.font_manager import FontManager
from core.utils.formatters import f_commas, f_pts
from core.utils.logger import Logger
from logic.dobumon.core.dob_battle_service import DobumonBattleService
from logic.dobumon.core.dob_breeding_service import DobumonBreedingService
from logic.dobumon.core.dob_buy_service import DobumonBuyService
from logic.dobumon.core.dob_exceptions import (
    DobumonError,
    DobumonInsufficientPointsError,
    DobumonNotFoundError,
)
from logic.dobumon.core.dob_formatter import DobumonFormatter
from logic.dobumon.core.dob_manager import DobumonManager
from logic.dobumon.core.dob_market_service import DobumonMarketService
from logic.dobumon.core.dob_training_service import DobumonTrainingService
from logic.dobumon.dob_shop.dob_shop_service import DobumonShopService
from logic.dobumon.training import TrainingEngine
from logic.dobumon.ui import (
    BreedSelectView,
    DobumonBuyView,
    DobumonMapSelectionView,
    DobumonSellView,
    MapSampleBreedView,
    RenameSkillView,
    TrainingView,
)
from logic.dobumon.ui.dob_battle import BattleAutoView, ChallengeView, DobumonSelectionView
from logic.dobumon.ui.dob_kinship_tree import DobumonKinshipTree
from logic.dobumon.ui.dob_shop_view import DobumonShopView
from logic.dobumon.ui.dob_status import StatusSelectionView
from logic.economy.status import StatusService
from managers.manager import game_manager


class DobumonCog(commands.Cog):
    """
    怒武者（ドブモン）関連のコマンドを提供するCog。
    UI操作と基本的なバリデーションを行い、重い処理は DobumonService に委譲します。
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # リポジトリを生成して Manager に注入
        repo = SQLiteDobumonRepository()
        self.manager = DobumonManager(repo)
        self.training_service = DobumonTrainingService(self.manager)
        self.breeding_service = DobumonBreedingService(self.manager)
        self.market_service = DobumonMarketService(self.manager)
        self.battle_service = DobumonBattleService(self.manager)
        self.shop_service = DobumonShopService(self.manager)
        self.buy_service = DobumonBuyService(self.manager)

        # エラーフォーマッターの登録
        BaseView.register_error_formatter(DobumonError, DobumonFormatter.format_error_embed)

        # 自然加齢タスクの開始
        self.aging_task.start()

    def cog_unload(self):
        """Cog取り外し時にタスクを停止"""
        self.aging_task.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        """起動時に中断されたセッションを復旧します"""
        await self.recover_sessions()

    async def recover_sessions(self):
        """中断された対戦セッションをクリーンアップまたは精算します"""
        sessions = game_manager.get_all_sessions()
        for session in sessions:
            if session.game_type != "dobumon_battle":
                continue

            Logger.info(
                "Dobumon",
                f"Recovering session in channel:{session.channel_id} (Status: {session.status})",
            )
            if session.status == "playing":
                try:
                    if session.battle_type == "wild":
                        self.manager.settle_wild_battle(
                            session.attacker_data["dobumon_id"],
                            session.winner_id == session.attacker_data["dobumon_id"],
                        )
                    else:
                        self.manager.settle_battle(session.winner_id, session.loser_id, reward=1000)
                    Logger.info(
                        "Dobumon", f"Recovered and settled session in channel:{session.channel_id}"
                    )
                except Exception as e:
                    Logger.error("Dobumon", f"Failed to settle recovered session: {e}")

            game_manager.end_session(session.channel_id)

    # --- Background Tasks ---

    @tasks.loop(time=datetime.time(hour=15, minute=0, tzinfo=datetime.timezone.utc))
    async def aging_task(self):
        """
        毎日 0:00 JST (15:00 UTC) に実行される自然加齢タスク。
        """
        Logger.info("Dobumon", "Starting scheduled natural aging process...")
        try:
            # 重いDB処理を同期的に実行（必要なら非同期ラッパーを通すが、現状は直接呼ぶ）
            # SQLiteなのでブロッキングを最小限にするため、ループ処理の合間に待機を入れることも検討可能
            result = self.manager.process_natural_aging()
            Logger.info(
                "Dobumon",
                f"Natural aging completed. Affected: {result['affected']}, Deaths: {result['deaths']}",
            )
        except Exception as e:
            Logger.error("Dobumon", f"Critical error in aging_task: {e}\n{traceback.format_exc()}")

    @aging_task.before_loop
    async def before_aging_task(self):
        """Botが準備完了するまで待機"""
        await self.bot.wait_until_ready()

    dobumon_group = app_commands.Group(
        name="dd-dobumon", description="怒武者（ドブモン）関連コマンド"
    )

    @dobumon_group.command(
        name="buy", description=f"バイヤーから怒武者を購入します ({f_pts(50000)})"
    )
    @check_maintenance()
    @defer_response(ephemeral=False)
    async def buy(self, interaction: discord.Interaction):
        """怒武者を購入するコマンド"""
        user_id = interaction.user.id
        cost = 50000

        balance = wallet.load_balance(user_id)
        if balance < cost:
            raise DobumonInsufficientPointsError(cost, balance)

        # 所持上限チェック
        self.manager.check_possession_limit(user_id)

        view = DobumonBuyView(interaction.user, self.buy_service)
        embed = view.create_embed()
        embed.add_field(name="所持金", value=f_pts(balance))

        await interaction.followup.send(embed=embed, view=view)
        Logger.info("Dobumon", f"User {interaction.user.display_name} opened buy wizard")

    @dobumon_group.command(name="status", description="所持している怒武者のステータスを確認します")
    @check_maintenance()
    @defer_response(ephemeral=True)
    async def status(self, interaction: discord.Interaction):
        """所持怒武者の一覧を表示するコマンド"""
        user_id = interaction.user.id
        dobumons = self.manager.get_user_dobumons(user_id, only_alive=True)

        if not dobumons:
            raise DobumonNotFoundError(
                "現在、生存している怒武者を所持していません。 `/dd-dobumon buy` で購入できます。"
            )

        view = StatusSelectionView(interaction.user, dobumons)
        summary_embed = StatusSelectionView.create_summary_embed(dobumons)

        await interaction.followup.send(embed=summary_embed, view=view)

    @dobumon_group.command(name="shop", description="アイテム屋を表示します。")
    @check_maintenance()
    @defer_response(ephemeral=True)
    async def shop(self, interaction: discord.Interaction):
        """怒武者ショップ・ウィザード"""
        user_id = interaction.user.id
        status = StatusService.get_user_status(user_id)
        dobumons = self.manager.get_user_dobumons(user_id, only_alive=True)

        view = DobumonShopView(
            user=interaction.user,
            shop_service=self.shop_service,
            user_status=status,
            user_dobumons=dobumons,
        )
        embed = view.create_embed()
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @dobumon_group.command(
        name="train", description=f"怒武者をトレーニングして強化します ({f_pts(500)} 〜)"
    )
    @check_maintenance()
    @defer_response(ephemeral=True)
    async def train(self, interaction: discord.Interaction):
        """ステータス強化ウィザード"""
        user_id = interaction.user.id
        dobumons = self.manager.get_user_dobumons(user_id, only_alive=True)
        if not dobumons:
            raise DobumonNotFoundError("トレーニング可能な怒武者を所持していません。")

        view = TrainingView(
            interaction.user,
            dobumons,
            self.training_service.execute_training,
            TrainingEngine.calculate_training_cost,
        )
        embed = discord.Embed(
            title="🏋️ トレーニング・ウィザード",
            description=f"トレーニングする怒武者と項目を選択してください。\n費用: **{f_pts(500)} 〜** (懐き度により割引あり)",
            color=0x3498DB,
        )
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @dobumon_group.command(
        name="rename-skill", description="習得した技に名前を付けます（一度のみ変更可能）"
    )
    @check_maintenance()
    @defer_response(ephemeral=True)
    async def rename_skill(self, interaction: discord.Interaction):
        """技の命名ウィザード"""
        user_id = interaction.user.id
        dobumons = self.manager.get_user_dobumons(user_id, only_alive=True)
        if not dobumons:
            raise DobumonNotFoundError("命名可能な怒武者を所持していません。")

        view = RenameSkillView(interaction.user, dobumons, self.market_service.execute_rename_skill)
        embed = discord.Embed(
            title="🏷️ 技の命名ウィザード",
            description="対象の怒武者と命名する技を選択してください。",
            color=0x9B59B6,
        )
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @dobumon_group.command(name="challenge", description="他のユーザーの怒武者に決闘を挑みます")
    @app_commands.describe(target="対戦相手")
    @check_maintenance()
    @defer_response(ephemeral=True)
    async def challenge(self, interaction: discord.Interaction, target: discord.Member):
        """決闘ウィザード"""
        await self.battle_service.execute_challenge(interaction, target)

    @dobumon_group.command(
        name="breed", description=f"2体の怒武者を交配させ、命を繋ぎます。費用: {f_pts(20000)}"
    )
    @check_maintenance()
    @defer_response(ephemeral=True)
    async def breed(self, interaction: discord.Interaction):
        """交配ウィザード"""
        user_id = interaction.user.id
        dobumons = self.manager.get_user_dobumons(user_id, only_alive=True)

        if len(dobumons) < 2:
            raise DobumonError("交配には少なくとも2体の怒武者が必要です。")

        # 所持上限チェック (交配によって新しく1体増えるため)
        self.manager.check_possession_limit(user_id)

        view = BreedSelectView(interaction.user, dobumons, self.breeding_service.execute_breed)
        embed = discord.Embed(
            title="🧬 交配ウィザード",
            description=f"交配させる両親を選択してください。\n費用: **{f_pts(20000)}**",
            color=discord.Color.gold(),
        )
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @dobumon_group.command(name="wild-battle", description="野生の怒武者と戦います")
    @check_maintenance()
    @defer_response(ephemeral=True)
    async def wild_battle(self, interaction: discord.Interaction):
        """野生戦ウィザード（ドブモン・難易度・マップ選択）"""
        await self.battle_service.execute_wild_battle(interaction)

    @dobumon_group.command(
        name="sell", description="所持している怒武者を売却してポイントを受け取ります"
    )
    @check_maintenance()
    @defer_response(ephemeral=True)
    async def sell(self, interaction: discord.Interaction):
        """売却ウィザード"""
        user_id = interaction.user.id
        dobumons = self.manager.get_user_dobumons(user_id, only_alive=True)
        if not dobumons:
            raise DobumonNotFoundError("売却可能な怒武者を所持していません。")

        view = DobumonSellView(
            interaction.user,
            dobumons,
            self.market_service.execute_sell,
            self.market_service.calculate_sell_price,
        )
        embed = discord.Embed(
            title="💰 売却ウィザード",
            description="売却する怒武者を選択してください。\n**警告: 売却した怒武者は二度と戻ってきません。**",
            color=0xF1C40F,
        )
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @dobumon_group.command(
        name="map", description="自分の所持している怒武者（ドブモン）のマップを表示します"
    )
    @app_commands.describe(target="特定のドブモンを中心に表示する場合、その名前またはIDを指定")
    @check_maintenance()
    @defer_response(ephemeral=False)
    async def map(self, interaction: discord.Interaction, target: str = None):
        """所持ドブモンのビジュアルマップを表示するコマンド"""
        user_id = interaction.user.id
        # 全個体を取得（死亡・売却済み含む）
        all_dobumons = self.manager.get_user_dobumons(user_id, only_alive=False)

        if not all_dobumons:
            raise DobumonNotFoundError(
                "所持している怒武者が見つかりませんでした。 `/dd-dobumon buy` で購入できます。"
            )

        if not target:
            # 引数なし: 生存している個体のみをドロップダウンに表示
            display_dobumons = [d for d in all_dobumons if d.is_alive]
            if not display_dobumons:
                raise DobumonNotFoundError("現在、生存している怒武者を所持していません。")

            desc = "マップを表示する怒武者を選択してください。\n（生存個体のみ表示されています）"
        else:
            # 引数あり: 名前またはIDが一致するすべての個体（生死不問）
            display_dobumons = [
                d for d in all_dobumons if d.name == target or d.dobumon_id == target
            ]
            if not display_dobumons:
                raise DobumonNotFoundError(f"「{target}」に一致する怒武者が見つかりませんでした。")

            desc = f"「{target}」に一致する個体が {len(display_dobumons)} 体見つかりました。\n表示する個体を選択してください。"

        # ビューの生成と送信
        view = DobumonMapSelectionView(
            interaction.user, all_dobumons, display_dobumons, self.manager.repo
        )
        embed = discord.Embed(
            title="〓 怒武者 血統地図（親等図） 〓",
            description=desc,
            color=0x34495E,
        )
        await interaction.followup.send(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(DobumonCog(bot))
