import datetime
from unittest.mock import MagicMock, patch

import pytest

from core.models.validation import UserSchema
from logic.dobumon.core.dob_buy_service import DobumonBuyService


@pytest.mark.asyncio
async def test_elite_syndicate_purchase_limit():
    """エリートシンジゲート（制限あり）の購入制限が機能するかテスト"""
    manager = MagicMock()
    buy_service = DobumonBuyService(manager)
    user_id = 12345
    shop_id = "syndicate"  # daily_limit: 1

    # 初期ユーザーデータ
    user_data = UserSchema(id=user_id, balance=2000000)

    # リポジトリのモック
    with patch("core.handlers.storage.SQLiteUserRepository") as mock_repo_class:
        mock_repo = mock_repo_class.return_value
        mock_repo.get_user.return_value = user_data

        # プレビューデータ
        preview_data = {
            "shop_id": shop_id,
            "iv": {"hp": 1.4, "atk": 1.4, "defense": 1.4, "eva": 1.4, "spd": 1.4},
            "has_mutation": False,
            "hint": "Awesome",
        }

        # Walletのモック
        with (
            patch("core.economy.wallet.load_balance", return_value=2000000),
            patch("core.economy.wallet.save_balance"),
            patch("core.economy.wallet.add_history"),
        ):
            # 1回目の購入：成功するはず
            dobu1 = await buy_service.execute_purchase(
                user_id=user_id,
                name="EliteDobu1",
                gender="M",
                attribute="fire",
                preview_data=preview_data,
            )
            assert dobu1.name == "EliteDobu1"

            # _update_buy_limit_data が呼ばれ、save_user が実行されているはず
            # mock_repo.save_user に渡された引数を確認
            assert mock_repo.save_user.called
            saved_user = mock_repo.save_user.call_args[0][0]
            today = datetime.date.today().isoformat()
            assert saved_user.dob_buy_data[shop_id]["last_buy_date"] == today
            assert saved_user.dob_buy_data[shop_id]["count"] == 1

            # 2回目の購入：制限エラーになるはず
            # mock_repo.get_user が更新されたデータを返すように設定
            mock_repo.get_user.return_value = saved_user

            with pytest.raises(ValueError) as excinfo:
                await buy_service.execute_purchase(
                    user_id=user_id,
                    name="EliteDobu2",
                    gender="F",
                    attribute="water",
                    preview_data=preview_data,
                )
            assert "購入上限に達しています" in str(excinfo.value)


@pytest.mark.asyncio
async def test_mart_no_purchase_limit():
    """ドブマート（制限なし）で複数回購入できるかテスト"""
    manager = MagicMock()
    buy_service = DobumonBuyService(manager)
    user_id = 12345
    shop_id = "mart"  # daily_limit: None

    user_data = UserSchema(id=user_id, balance=2000000)

    with patch("core.handlers.storage.SQLiteUserRepository") as mock_repo_class:
        mock_repo = mock_repo_class.return_value
        mock_repo.get_user.return_value = user_data

        preview_data = {
            "shop_id": shop_id,
            "iv": {"hp": 1.0, "atk": 1.0, "defense": 1.0, "eva": 1.0, "spd": 1.0},
            "has_mutation": False,
            "hint": "Normal",
        }

        with (
            patch("core.economy.wallet.load_balance", return_value=2000000),
            patch("core.economy.wallet.save_balance"),
            patch("core.economy.wallet.add_history"),
        ):
            # 1回目の購入
            await buy_service.execute_purchase(
                user_id=user_id,
                name="Dobu1",
                gender="M",
                attribute="fire",
                preview_data=preview_data,
            )

            # 2回目の購入：制限がないので成功するはず
            await buy_service.execute_purchase(
                user_id=user_id,
                name="Dobu2",
                gender="F",
                attribute="water",
                preview_data=preview_data,
            )
            # 例外が発生しなければパス
