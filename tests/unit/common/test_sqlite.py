import os

import pytest

from core.handlers.storage import (
    SQLiteDobumonRepository,
    SQLiteSessionRepository,
    SQLiteSystemRepository,
    SQLiteUserRepository,
)
from core.models.validation import DobumonSchema, SessionSchemaType, UserSchema
from core.utils.exceptions import DataValidationError


class TestSQLiteRepositories:
    @pytest.fixture(autouse=True)
    def setup_method(self, tmp_path):
        db_file = tmp_path / "test_repos.db"
        self.db_path = str(db_file)
        self.user_repo = SQLiteUserRepository(self.db_path)
        self.session_repo = SQLiteSessionRepository(self.db_path)
        self.system_repo = SQLiteSystemRepository(self.db_path)
        self.dob_repo = SQLiteDobumonRepository(self.db_path)

    def test_user_repository(self):
        user_id = 999
        user = UserSchema(id=user_id, balance=50000, last_daily="2023-01-01")
        self.user_repo.save_user(user)

        saved = self.user_repo.get_user(user_id)
        assert saved.balance == 50000
        assert saved.id == user_id

        # 全ユーザー取得
        self.user_repo.save_user(UserSchema(id=888, balance=100))
        all_users = self.user_repo.get_all_users()
        assert len(all_users) == 2

    def test_session_repository(self):
        chan_id = 12345
        from pydantic import TypeAdapter

        adapter = TypeAdapter(SessionSchemaType)
        session_data = {
            "channel_id": chan_id,
            "game_type": "chinchiro",
            "status": "playing",
            "host_id": 999,
            "bet_amount": 100,
            "pot": 200,
            "players": [{"id": 999}, {"id": 888}],
        }
        model = adapter.validate_python(session_data)
        self.session_repo.save_session(model)

        loaded = self.session_repo.get_session(chan_id)
        assert loaded.pot == 200
        assert loaded.game_type == "chinchiro"

        self.session_repo.delete_session(chan_id)
        assert self.session_repo.get_session(chan_id) is None

    def test_dobumon_repository(self):
        # 怒武者データの CRUD
        dobu_id = "test-uuid-1"
        dobu = DobumonSchema(
            dobumon_id=dobu_id,
            owner_id=123,
            name="リポドブ",
            gender="M",
            hp=100.0,
            atk=50.0,
            defense=50.0,
            eva=10.0,
            spd=10.0,
        )
        self.dob_repo.save_dobumon(dobu)

        saved = self.dob_repo.get_dobumon(dobu_id)
        assert saved.name == "リポドブ"
        assert saved.dobumon_id == dobu_id

        # ユーザー所属の取得
        user_dobus = self.dob_repo.get_user_dobumons(123)
        assert len(user_dobus) == 1
        assert user_dobus[0].dobumon_id == dobu_id
