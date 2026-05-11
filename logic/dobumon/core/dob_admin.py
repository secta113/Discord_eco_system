from typing import Tuple

from core.handlers.storage import IDobumonRepository
from logic.dobumon.core.dob_models import Dobumon


class DobumonAdminAction:
    """
    ドブモンの管理操作（蘇生、名前変更、削除など）を担当するクラス。
    """

    def __init__(self, repo: IDobumonRepository):
        self.repo = repo

    def revive_dobumon_by_name(self, name: str) -> Tuple[bool, str]:
        """
        名前を指定して死亡した怒武者を生き返らせます。
        """
        # 名前で検索
        models = self.repo.get_dobumons_by_name(name)
        if not models:
            return False, f"名前 '{name}' の個体が見つかりませんでした。"

        # 既に生きているものを除外
        dead_only = [m for m in models if not m.is_alive]
        if not dead_only:
            return False, f"名前 '{name}' の個体は既に生存しているか、見つかりませんでした。"

        if len(dead_only) > 1:
            ids = [d.dobumon_id[:8] for d in dead_only]
            return (
                False,
                f"同名の死亡個体が複数見つかりました。IDを指定して手動で対応してください: {', '.join(ids)}",
            )

        # 蘇生
        model = dead_only[0]
        dobu = Dobumon(**model.model_dump())
        dobu.revive()
        # 元のmanager.save_dobumonはrepo.save_dobumon(model)を呼んでいた
        # Repoが必要なのはDobumonSchemaか
        from core.models.validation import DobumonSchema

        self.repo.save_dobumon(DobumonSchema(**dobu.to_dict()))

        return True, f"DONE: {dobu.name} (Owner: {dobu.owner_id}) を蘇生しました。"

    def rename_dobumon_by_name(self, old_name: str, new_name: str) -> Tuple[bool, str]:
        """
        名前を指定して怒武者の名前を変更します。
        """
        models = self.repo.get_dobumons_by_name(old_name)
        if not models:
            return False, f"名前 '{old_name}' の個体が見つかりませんでした。"

        if len(models) > 1:
            ids = [m.dobumon_id[:8] for m in models]
            return (
                False,
                f"同名の個体が複数見つかりました。IDを指定して手動で対応してください: {', '.join(ids)}",
            )

        # 変更
        model = models[0]
        dobu = Dobumon(**model.model_dump())
        dobu.name = new_name

        from core.models.validation import DobumonSchema

        self.repo.save_dobumon(DobumonSchema(**dobu.to_dict()))

        return True, f"DONE: {old_name} を {new_name} に変更しました (ID: {dobu.dobumon_id[:8]})。"

    def delete_dobumon(self, dobumon_id: str):
        """データベースから完全に削除します。"""
        self.repo.delete_dobumon(dobumon_id)
