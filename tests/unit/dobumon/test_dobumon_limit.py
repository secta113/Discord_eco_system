from unittest.mock import MagicMock

import pytest

from logic.dobumon.core.dob_constants import MAX_DOBUMON_POSSESSION
from logic.dobumon.core.dob_exceptions import DobumonError
from logic.dobumon.core.dob_manager import DobumonManager


def test_possession_limit():
    repo = MagicMock()
    manager = DobumonManager(repo)

    owner_id = 123
    # 既存が MAX_DOBUMON_POSSESSION 体いる状態をシミュレート
    repo.get_user_dobumons.return_value = [MagicMock()] * MAX_DOBUMON_POSSESSION

    with pytest.raises(DobumonError) as excinfo:
        manager.check_possession_limit(owner_id)

    assert str(MAX_DOBUMON_POSSESSION) in str(excinfo.value)
    assert "所持しています" in str(excinfo.value)


def test_possession_limit_ok():
    repo = MagicMock()
    manager = DobumonManager(repo)

    owner_id = 123
    # 制限以下の所持数
    repo.get_user_dobumons.return_value = [MagicMock()] * (MAX_DOBUMON_POSSESSION - 1)

    # 例外が発生しないこと
    manager.check_possession_limit(owner_id)
