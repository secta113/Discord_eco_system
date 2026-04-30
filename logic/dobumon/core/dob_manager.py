import traceback
from typing import Dict, List, Optional

from core.handlers.storage import IDobumonRepository
from core.utils.logger import Logger
from logic.dobumon.core.dob_admin import DobumonAdminAction
from logic.dobumon.core.dob_chronicle import DobumonChronicle
from logic.dobumon.core.dob_constants import MAX_DOBUMON_POSSESSION
from logic.dobumon.core.dob_exceptions import DobumonError, DobumonNotFoundError
from logic.dobumon.core.dob_factory import DobumonFactory
from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.dob_battle.battle_handler import BattleHandler
from logic.dobumon.dob_battle.wild.wild_handler import WildHandler
from logic.dobumon.genetics.breeding_handler import BreedingHandler

# ハンドラーのインポート
from logic.dobumon.training.training_handler import TrainingHandler

# 開発中フラグ: 死亡を無効化する場合は True に設定します
DISABLE_DEATH = True


class DobumonManager:
    """
    怒武者（ドブモン）の生成、保存、取得を管理するクラス。
    各機能（育成、戦闘、交配等）の実装は専門のハンドラーに委譲します。
    """

    def __init__(self, repo: IDobumonRepository):
        self.repo = repo
        self._admin = DobumonAdminAction(repo)
        self._chronicle = DobumonChronicle(repo, self.handle_death, self.save_dobumon)

        # ハンドラーの初期化
        self._training = TrainingHandler(self)
        self._battle = BattleHandler(self)
        self._wild = WildHandler(self)
        self._breeding = BreedingHandler(self)

    def handle_death(self, dobu: Dobumon, reason: str) -> bool:
        """
        ドブモンの死亡イベントを処理します。
        特性により死亡が無効化されている場合、または開発フラグが有効な場合は死亡をキャンセルします。
        ※寿命・加齢による死亡は無効化できません。

        Returns:
            bool: 実際に死亡した場合は True、回避された場合は False
        """
        # 寿命・加齢による死亡チェック (デバッグモードや特性に関わらず常に死亡)
        is_lifespan_death = any(k in reason for k in ["Lifespan", "Aging"])
        if is_lifespan_death:
            dobu.die()
            Logger.info(
                "Dobumon",
                f"Death Occurred (Lifespan/Aging) [ {dobu.name} ] ({dobu.dobumon_id}) - Reason: {reason}",
            )
            return True

        # 特性のチェック: 戦闘での死亡を逃れる特性（不死など）
        is_combat_death = any(k in reason for k in ["PvP", "Wild", "Battle"])
        if is_combat_death:
            from logic.dobumon.core.dob_traits import TraitRegistry

            if any(TraitRegistry.get(t).modifies_battle_death() for t in dobu.traits):
                Logger.info(
                    "Dobumon",
                    f"Death Prevented by Trait [ {dobu.name} ] ({dobu.dobumon_id}) - Reason: {reason}",
                )
                dobu.health = max(1.0, dobu.health)
                return False

        if DISABLE_DEATH:
            Logger.info(
                "Dobumon",
                f"Death Prevented [ {dobu.name} ] ({dobu.dobumon_id}) - Reason: {reason} (DISABLE_DEATH is True)",
            )
            # 死亡はさせないが、HPは1程度にしておく（戦闘不能状態の表現）
            dobu.health = max(1.0, dobu.health)
            return False

        dobu.die()
        Logger.info(
            "Dobumon",
            f"Death Occurred [ {dobu.name} ] ({dobu.dobumon_id}) - Reason: {reason}",
        )
        return True

    def create_dobumon(
        self,
        owner_id: int,
        name: str,
        source: str = "buyer",
        gender: str = None,
        attribute: str = None,
    ) -> Dobumon:
        """
        新しい怒武者を生成します。
        """
        return DobumonFactory.create_new(owner_id, name, source, gender, attribute)

    def save_dobumon(self, dobu: Dobumon):
        """データベースに保存します。"""
        try:
            from core.models.validation import DobumonSchema

            model = DobumonSchema(**dobu.to_dict())
            self.repo.save_dobumon(model)
        except Exception as e:
            Logger.error(
                "Dobumon",
                f"Failed to save dobumon {dobu.dobumon_id}: {e}\n{traceback.format_exc()}",
            )
            raise

    def get_user_dobumons(self, owner_id: int, only_alive: bool = True) -> List[Dobumon]:
        """指定したユーザーの怒武者一覧を取得します。"""
        models = self.repo.get_user_dobumons(owner_id, only_alive)
        return [Dobumon(**m.model_dump()) for m in models]

    def get_user_dobumons_count(self, owner_id: int, only_alive: bool = True) -> int:
        """指定したユーザーが所持している怒武者の数を取得します。"""
        return len(self.repo.get_user_dobumons(owner_id, only_alive))

    def check_possession_limit(self, owner_id: int):
        """所持上限に達しているかチェックします。"""
        count = self.get_user_dobumons_count(owner_id, only_alive=True)
        if count >= MAX_DOBUMON_POSSESSION:
            raise DobumonError(
                f"既に {MAX_DOBUMON_POSSESSION} 体の怒武者を所持しています。これ以上は獲得できません。"
            )

    def get_dobumon(self, dobumon_id: str) -> Optional[Dobumon]:
        """IDを指定して怒武者を取得します。"""
        model = self.repo.get_dobumon(dobumon_id)
        if not model:
            return None
        return Dobumon(**model.model_dump())

    # --- Delegated to TrainingHandler ---

    def train_menu(self, dobumon_id: str, menu_key: str):
        return self._training.train_menu(dobumon_id, menu_key)

    def rename_skill(self, dobumon_id: str, skill_index: int, new_name: str):
        return self._training.rename_skill(dobumon_id, skill_index, new_name)

    # --- Delegated to BattleHandler (PvP) ---

    def settle_battle(self, winner_id: str, loser_id: str, battle_result: Dict = None) -> Dict:
        return self._battle.settle_battle(winner_id, loser_id, battle_result)

    # --- Delegated to WildHandler (Wild Battle) ---

    def create_wild_dobumon(self, player_dobu: Dobumon, rank_key: str = "C") -> Dobumon:
        return self._wild.create_wild_dobumon(player_dobu, rank_key)

    def settle_wild_battle(
        self,
        winner_id: str,
        player_dobu_id: str,
        wild_dobu: Dobumon,
        rank_key: str = "C",
        battle_result: Dict = None,
    ) -> Dict:
        return self._wild.settle_wild_battle(
            winner_id, player_dobu_id, wild_dobu, rank_key, battle_result
        )

    # --- Delegated to BreedingHandler ---

    def breed_dobumon(self, parent1_id: str, parent2_id: str, child_name: str) -> Dict:
        return self._breeding.breed_dobumon(parent1_id, parent2_id, child_name)

    # --- Delegated Admin Actions ---

    def revive_dobumon_by_name(self, name: str) -> tuple[bool, str]:
        return self._admin.revive_dobumon_by_name(name)

    def rename_dobumon_by_name(self, old_name: str, new_name: str) -> tuple[bool, str]:
        return self._admin.rename_dobumon_by_name(old_name, new_name)

    def delete_dobumon(self, dobumon_id: str):
        self._admin.delete_dobumon(dobumon_id)

    # --- Delegated Chronicle Actions ---

    def process_natural_aging(self) -> Dict:
        return self._chronicle.process_natural_aging()
