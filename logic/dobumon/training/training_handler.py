from core.utils.time_utils import get_jst_today
from logic.dobumon.core.dob_exceptions import DobumonError, DobumonNotFoundError
from logic.dobumon.core.dob_logger import DobumonLogger
from logic.dobumon.training import (
    TrainingEngine,
    check_and_learn_skill,
    rename_skill,
)


class TrainingHandler:
    """
    怒武者のトレーニングとスキル管理を担当するハンドラー。
    """

    def __init__(self, manager):
        self.manager = manager

    def train_menu(self, dobumon_id: str, menu_key: str):
        """
        特定のメニューでトレーニングを実行します。
        """
        dobu = self.manager.get_dobumon(dobumon_id)
        if not dobu or not dobu.is_alive:
            raise DobumonNotFoundError()

        # 日付チェックとカウントリセット
        today_str = get_jst_today()

        if dobu.last_train_date != today_str:
            dobu.today_train_count = 0
            dobu.today_wild_battle_count = 0
            dobu.today_affection_gain = 0
            dobu.today_massage_count = 0
            dobu.last_train_date = today_str

        # トレーニング計算実行
        result = TrainingEngine.calculate_menu_gains(dobu, menu_key)
        if not result["success"]:
            raise DobumonError(result["msg"])

        # トレーニング結果の適用
        update_info = TrainingEngine.apply_training_results(dobu, result)

        # マッサージ回数カウントの更新
        if menu_key == "massage":
            dobu.today_massage_count += 1

        # 死亡判定の集約
        if not update_info["is_alive"] and dobu.is_alive:
            self.manager.handle_death(dobu, f"Training Overwork ({menu_key})")
            # handle_death によって無効化された場合、update_info のフラグも戻す
            update_info["is_alive"] = dobu.is_alive

        learned_skill = None
        if menu_key != "massage":
            learned_skill = check_and_learn_skill(dobu)

        self.manager.save_dobumon(dobu)

        DobumonLogger.training(dobu, menu_key, result.get("gains"), dobu.is_alive)

        final_result = result.copy()
        final_result.update(update_info)
        final_result.update(
            {
                "learned_skill": learned_skill,
                "affection_total": dobu.affection,
                "health_current": dobu.health,
                "health_max": dobu.hp,
            }
        )
        return True, final_result

    def rename_skill(self, dobumon_id: str, skill_index: int, new_name: str):
        """
        技の名前を変更します。
        """
        dobu = self.manager.get_dobumon(dobumon_id)
        if not dobu:
            raise DobumonNotFoundError()

        success, msg = rename_skill(dobu, skill_index, new_name)
        if success:
            self.manager.save_dobumon(dobu)
        return success, msg
