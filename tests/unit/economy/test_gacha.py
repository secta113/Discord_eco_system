from unittest.mock import patch

import pytest

from core.economy import wallet
from core.handlers.storage import SQLiteSystemRepository, SQLiteUserRepository
from logic.economy.eco_exceptions import GachaLimitReachedError
from logic.gacha_service import gacha_service


class TestGachaV16:
    USER_ID = 999999

    @pytest.fixture(autouse=True)
    def setup_method(self, tmp_path):
        # テスト用のテンポラリDBを作成してwalletに注入
        db_file = tmp_path / "test_gacha.db"
        user_repo = SQLiteUserRepository(str(db_file))
        system_repo = SQLiteSystemRepository(str(db_file))

        with (
            patch.object(wallet, "user_repo", user_repo),
            patch.object(wallet, "system_repo", system_repo),
        ):
            # 状態リセット (テスト用DBに対して行われる)
            wallet.set_last_gacha_daily(self.USER_ID, "1970-01-01")
            wallet.set_gacha_count(self.USER_ID, 0)
            wallet.save_balance(self.USER_ID, 10000)
            yield

    def test_gacha_flow(self):
        # 1. 1st Gacha (Guaranteed New)
        cost = gacha_service.get_current_cost(self.USER_ID)
        assert cost == 500

        result = gacha_service.execute_gacha(self.USER_ID)
        assert result["cost"] == 500
        assert result["count_today"] == 1
        assert result["is_guaranteed_new"] is True

        # 2. 2nd Gacha (1000 pts)
        cost = gacha_service.get_current_cost(self.USER_ID)
        assert cost == 1000
        result = gacha_service.execute_gacha(self.USER_ID)
        assert result["cost"] == 1000

        # 3. 3rd Gacha (1500 pts)
        result = gacha_service.execute_gacha(self.USER_ID)
        assert result["cost"] == 1500

        # 4. 4th Gacha (Should Fail)
        with pytest.raises(GachaLimitReachedError) as excinfo:
            gacha_service.execute_gacha(self.USER_ID)
        assert "上限" in str(excinfo.value) or "回" in str(excinfo.value)
