import datetime
import random
from typing import Any, Dict, Optional

from core.economy import wallet
from logic.dobumon.core.dob_factory import DobumonFactory
from logic.dobumon.core.dob_logger import DobumonLogger
from logic.dobumon.core.dob_manager import DobumonManager
from logic.dobumon.core.dob_models import Dobumon

SHOP_CONFIGS = {
    "mart": {
        "name": "ドブマート",
        "description": "一般的な怒武者を扱う量販店。品質は安定しているが、特筆すべき点はない。",
        "price": 50000,
        "iv_range": (0.9, 1.1),
        "mutation_chance": 0.0,
        "daily_limit": None,
        "color": 0x95A5A6,
        "emoji": "🛒",
    },
    "breeder": {
        "name": "高級ブリーダー",
        "description": "血統を重視したプロのブリーダー。優れた素質を持つ個体が多く、稀に突然変異も確認される。",
        "price": 200000,
        "iv_range": (1.1, 1.3),
        "mutation_chance": 0.0001,
        "daily_limit": None,
        "color": 0x3498DB,
        "emoji": "🏠",
    },
    "syndicate": {
        "name": "エリート・シンジケート",
        "description": "裏社会のコネクションを駆使して集められた最上級個体。その実力は折り紙付きだが、入手は困難。",
        "price": 1000000,
        "iv_range": (1.3, 1.5),
        "mutation_chance": 0.10,
        "daily_limit": 1,
        "color": 0xE74C3C,
        "emoji": "🕶️",
    },
}


class DobumonBuyService:
    """
    怒武者の購入ロジックを集約するサービスクラス。
    """

    def __init__(self, manager: DobumonManager):
        self.manager = manager

    def get_shop_config(self, shop_id: str) -> Optional[Dict[str, Any]]:
        return SHOP_CONFIGS.get(shop_id)

    def check_purchase_limit(self, user_id: int, shop_id: str) -> bool:
        """
        購入制限をチェックします。
        """
        config = self.get_shop_config(shop_id)
        if not config or config["daily_limit"] is None:
            return True

        from core.handlers.storage import SQLiteUserRepository

        user_repo = SQLiteUserRepository()
        user = user_repo.get_user(user_id)
        if not user:
            return True

        buy_data = user.dob_buy_data or {}
        shop_data = buy_data.get(shop_id, {})

        last_buy_date = shop_data.get("last_buy_date")
        today = datetime.date.today().isoformat()

        if last_buy_date == today:
            count = shop_data.get("count", 0)
            if count >= config["daily_limit"]:
                return False

        return True

    def generate_preview(self, shop_id: str) -> Dict[str, Any]:
        """
        購入前のプレビュー個体を生成します（保存はしません）。
        """
        config = self.get_shop_config(shop_id)
        if not config:
            raise ValueError(f"Invalid shop_id: {shop_id}")

        iv_range = config["iv_range"]
        iv = {
            "hp": round(random.uniform(*iv_range), 2),
            "atk": round(random.uniform(*iv_range), 2),
            "defense": round(random.uniform(*iv_range), 2),
            "eva": round(random.uniform(*iv_range), 2),
            "spd": round(random.uniform(*iv_range), 2),
        }

        has_mutation = random.random() < config["mutation_chance"]
        hint = DobumonFactory.generate_iv_hints(iv)

        if has_mutation:
            hint += "\nこの個体からは、何か未知のエネルギーを感じる……！"

        return {
            "iv": iv,
            "has_mutation": has_mutation,
            "hint": hint,
            "shop_id": shop_id,
        }

    async def execute_purchase(
        self,
        user_id: int,
        name: str,
        gender: str,
        attribute: str,
        preview_data: Dict[str, Any],
    ) -> Dobumon:
        """
        購入を確定し、怒武者を生成・保存します。
        """
        shop_id = preview_data["shop_id"]
        config = self.get_shop_config(shop_id)
        if not config:
            raise ValueError(f"Invalid shop_id: {shop_id}")

        # 1. 資産チェック
        balance = wallet.load_balance(user_id)
        if balance < config["price"]:
            from logic.dobumon.core.dob_exceptions import DobumonInsufficientPointsError

            raise DobumonInsufficientPointsError(config["price"], balance)

        # 2. 購入制限チェック
        if not self.check_purchase_limit(user_id, shop_id):
            raise ValueError(f"本日の「{config['name']}」での購入上限に達しています。")

        # 3. 所持上限チェック
        self.manager.check_possession_limit(user_id)

        # 4. 支払い
        wallet.save_balance(user_id, balance - config["price"])
        wallet.add_history(user_id, f"怒武者「{name}」購入 ({config['name']})", -config["price"])

        # 5. 生成
        dobu = DobumonFactory.create_new(
            owner_id=user_id,
            name=name,
            source=f"shop_{shop_id}",
            gender=gender,
            attribute=attribute,
            custom_iv=preview_data["iv"],
            force_mutation=preview_data["has_mutation"],
        )
        self.manager.save_dobumon(dobu)
        self._update_buy_limit_data(user_id, shop_id)

        DobumonLogger.action(str(user_id), "purchased", name, f"from '{shop_id}'")
        return dobu

    def _update_buy_limit_data(self, user_id: int, shop_id: str):
        """
        購入制限データをデータベースに保存します。
        """
        from core.handlers.storage import SQLiteUserRepository

        user_repo = SQLiteUserRepository()
        user = user_repo.get_user(user_id)
        if not user:
            return

        buy_data = user.dob_buy_data or {}
        shop_data = buy_data.get(shop_id, {})

        today = datetime.date.today().isoformat()
        if shop_data.get("last_buy_date") == today:
            shop_data["count"] = shop_data.get("count", 0) + 1
        else:
            shop_data["last_buy_date"] = today
            shop_data["count"] = 1

        buy_data[shop_id] = shop_data
        user.dob_buy_data = buy_data
        user_repo.save_user(user)
