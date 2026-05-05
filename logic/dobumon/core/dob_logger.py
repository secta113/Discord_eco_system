from core.utils.logger import Logger
from logic.dobumon.core.dob_models import Dobumon


class DobumonLogger:
    """
    怒武者（ドブモン）関連のログ出力を一括管理するクラス。
    """

    @staticmethod
    def action(user_name: str, action_type: str, target_name: str, details: str = ""):
        """ユーザーによる具体的なアクション（購入、交配、育成開始など）を記録します。"""
        msg = f"[Action] User {user_name} {action_type} {target_name}"
        if details:
            msg += f" ({details})"
        Logger.info("Dobumon", msg)

    @staticmethod
    def genetics(dobu: Dobumon, context: str = "Created", p1_name: str = None, p2_name: str = None):
        """個体のスペックや遺伝情報（誕生、交配結果）を詳細に記録します。"""
        avg_iv = sum(dobu.iv.values()) / len(dobu.iv) if dobu.iv else 0.0

        parents_info = ""
        if p1_name and p2_name:
            parents_info = f" | Parents: {p1_name} + {p2_name}"

        msg = (
            f"[{context}] {dobu.name}({dobu.dobumon_id[:8]})"
            f"{parents_info} | Gen:{dobu.generation} | Attr:{dobu.attribute} "
            f"| Traits:{dobu.traits} | Taboo:{dobu.genetics.get('forbidden_depth', 0)} "
            f"| IV:{avg_iv:.2f}"
        )
        Logger.info("Dobumon", msg)

    @staticmethod
    def training(dobu: Dobumon, menu: str, gains: dict, alive: bool):
        """トレーニングの結果（上昇値や生存確認）を記録します。"""
        msg = (
            f"[Logic] Train Result: {dobu.name}({dobu.dobumon_id[:8]}) on '{menu}' "
            f"| Gains: {gains} | Alive: {alive}"
        )
        Logger.info("Dobumon", msg)

    @staticmethod
    def market(user_name: str, action: str, dobu: Dobumon, price: int = 0):
        """売却や命名などの市場・管理操作を記録します。"""
        from core.utils.formatters import f_pts

        price_info = f" for {f_pts(price)}" if price > 0 else ""
        msg = f"[Market] User {user_name} {action} {dobu.name}({dobu.dobumon_id[:8]}){price_info}"
        Logger.info("Dobumon", msg)

    @staticmethod
    def death(dobu: Dobumon, reason: str, is_prevented: bool = False):
        """死亡イベント（またはその回避）を記録します。"""
        status = "Prevented" if is_prevented else "Occurred"
        msg = f"[Life] Death {status} [ {dobu.name} ] ({dobu.dobumon_id[:8]}) - Reason: {reason}"
        Logger.info("Dobumon", msg)

    @staticmethod
    def aging(dobu: Dobumon, old_life: float, new_life: float, mod: float):
        """自然加齢による寿命の変化を記録します。"""
        msg = (
            f"[Chronicle] Aging [ {dobu.name} ]: {old_life:.2f} -> {new_life:.2f} (mod: {mod:.2f})"
        )
        Logger.info("Dobumon", msg)

    @staticmethod
    def battle(action: str, details: str):
        """戦闘関連のイベント（開始、終了、タイムアウトなど）を記録します。"""
        msg = f"[Battle] {action}: {details}"
        Logger.info("Dobumon", msg)

    @staticmethod
    def shop(action: str, details: str):
        """ショップ関連のイベント（アイテム購入など）を記録します。"""
        msg = f"[Shop] {action}: {details}"
        Logger.info("Dobumon", msg)

    @staticmethod
    def skill(dobu: Dobumon, action: str, skill_name: str):
        """技の習得などのイベントを記録します。"""
        msg = f"[Skill] {dobu.name}({dobu.dobumon_id[:8]}) {action}: {skill_name}"
        Logger.info("Dobumon", msg)
