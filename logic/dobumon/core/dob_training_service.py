import discord

from core.economy import wallet
from logic.dobumon.core.dob_exceptions import (
    DobumonExecutionError,
    DobumonInsufficientPointsError,
    DobumonNotFoundError,
)
from logic.dobumon.core.dob_formatter import DobumonFormatter
from logic.dobumon.core.dob_logger import DobumonLogger
from logic.dobumon.core.dob_manager import DobumonManager
from logic.dobumon.training import TrainingEngine
from logic.dobumon.ui import (
    TrainingResultView,
)


class DobumonTrainingService:
    """
    怒武者のトレーニング実行ロジックを管理するサービス。
    """

    def __init__(self, manager: DobumonManager):
        self.manager = manager

    async def execute_training(self, interaction: discord.Interaction, dobumon_id: str, menu: str):
        """練習メニューの実行ロジック本体"""
        user_id = interaction.user.id
        dobu = self.manager.get_dobumon(dobumon_id)
        if not dobu or not dobu.is_alive:
            raise DobumonNotFoundError()

        cost = TrainingEngine.calculate_training_cost(dobu)
        balance = wallet.load_balance(user_id)
        if balance < cost:
            raise DobumonInsufficientPointsError(
                cost, balance, context=f"※本日の{dobu.today_train_count + 1}回目の育成費用です。"
            )

        success, result = self.manager.train_menu(dobumon_id, menu)
        if not success:
            raise DobumonExecutionError(result)

        wallet.save_balance(user_id, balance - cost)
        wallet.add_history(user_id, f"怒武者トレーニング ({menu})", -cost)

        embed = DobumonFormatter.format_training_result_embed(dobu, menu, result)

        # 継続ボタン付きViewの作成（生存している場合）
        view = (
            TrainingResultView(interaction.user, self.manager, self, dobumon_id)
            if result["is_alive"]
            else None
        )

        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view)

        DobumonLogger.action(interaction.user.display_name, "trained", dobu.name, f"on '{menu}'")
