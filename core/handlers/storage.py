import os
from typing import Dict, List, Optional, Protocol

from pydantic import TypeAdapter

from core.handlers import sql_handler
from core.models import validation
from core.models.validation import (
    DobumonSchema,
    SessionSchemaType,
    UserSchema,
)
from core.utils.exceptions import DataValidationError, StorageError
from core.utils.logger import Logger


class DatabaseConfig:
    _db_path: Optional[str] = None

    @classmethod
    def get_db_path(cls) -> str:
        if cls._db_path is not None:
            return cls._db_path
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(root_dir, "data", "discord_eco_sys.db")

    @classmethod
    def set_db_path(cls, path: str) -> None:
        cls._db_path = path


class IUserRepository(Protocol):
    def get_user(self, user_id: int) -> Optional[UserSchema]: ...
    def save_user(self, user: UserSchema) -> None: ...
    def get_all_users(self) -> Dict[int, UserSchema]: ...


class ISessionRepository(Protocol):
    def get_session(self, channel_id: int) -> Optional[SessionSchemaType]: ...
    def save_session(self, session: SessionSchemaType) -> None: ...
    def delete_session(self, channel_id: int) -> None: ...
    def get_all_sessions(self) -> Dict[str, SessionSchemaType]: ...


class IDobumonRepository(Protocol):
    def get_dobumon(self, dobumon_id: str) -> Optional[DobumonSchema]: ...
    def save_dobumon(self, dobumon: DobumonSchema) -> None: ...
    def get_user_dobumons(self, owner_id: int, only_alive: bool = True) -> List[DobumonSchema]: ...
    def get_dobumons_by_name(self, name: str) -> List[DobumonSchema]: ...
    def get_all_alive_dobumons(self) -> List[DobumonSchema]: ...
    def delete_dobumon(self, dobumon_id: str) -> None: ...


class ISystemRepository(Protocol):
    def get_system_data(self, key: str) -> Optional[Dict]: ...
    def save_system_data(self, key: str, data: Dict) -> None: ...
    def log_jackpot(
        self,
        user_id: int,
        game_type: str,
        hand_name: str,
        rarity: str,
        amount: int,
        pool_after: int,
    ) -> None: ...


class SQLiteBaseRepository:
    def __init__(self, db_path: str = None):
        self.db_path = db_path if db_path is not None else DatabaseConfig.get_db_path()

        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        sql_handler.init_db(self.db_path)


class SQLiteUserRepository(SQLiteBaseRepository, IUserRepository):
    def get_user(self, user_id: int) -> Optional[UserSchema]:
        if user_id < 0:
            return None
        try:
            data = sql_handler.get_user(self.db_path, user_id)
            if data and "id" not in data:
                data["id"] = user_id
            return UserSchema(**data) if data else None
        except Exception as e:
            Logger.error("Storage", f"SQLite Get User Error: {e}", exc_info=True)
            raise StorageError(f"ユーザー情報の取得に失敗しました: {e}")

    def save_user(self, user: UserSchema) -> None:
        user_id = user.id
        if user_id < 0:
            return
        try:
            data = user.model_dump()
            validation.validate_user_data(data)
            sql_handler.upsert_user(
                self.db_path,
                user_id,
                data["balance"],
                data["last_daily"],
                data["history"],
                data["total_wins"],
                data["games_played"],
                data["max_win_amount"],
                last_gacha_daily=data["last_gacha_daily"],
                gacha_collection=data["gacha_collection"],
                gacha_count_today=data["gacha_count_today"],
                last_wild_battle_date=data["last_wild_battle_date"],
                wild_battle_count_today=data["wild_battle_count_today"],
                dob_buy_data=data["dob_buy_data"],
            )
        except Exception as e:
            if isinstance(e, (ValueError, DataValidationError)):
                raise
            Logger.error("Storage", f"SQLite Save User Error: {e}", exc_info=True)
            raise StorageError(f"ユーザー情報の保存に失敗しました: {e}")

    def get_all_users(self) -> Dict[int, UserSchema]:
        try:
            all_data = sql_handler.get_all_users(self.db_path)
            res = {}
            for uid, data in all_data.items():
                if "id" not in data:
                    data["id"] = uid
                res[uid] = UserSchema(**data)
            return res
        except Exception as e:
            Logger.error("Storage", f"SQLite Get All Users Error: {e}", exc_info=True)
            raise StorageError(f"全ユーザー情報の取得に失敗しました: {e}")


class SQLiteSessionRepository(SQLiteBaseRepository, ISessionRepository):
    def get_session(self, channel_id: int) -> Optional[SessionSchemaType]:
        try:
            data = sql_handler.get_session(self.db_path, channel_id)
            if not data:
                return None
            adapter = TypeAdapter(SessionSchemaType)
            return adapter.validate_python(data)
        except Exception as e:
            Logger.error("Storage", f"SQLite Get Session Error: {e}", exc_info=True)
            raise StorageError(f"セッション情報の取得に失敗しました: {e}")

    def save_session(self, session: SessionSchemaType) -> None:
        channel_id = session.channel_id
        try:
            data = session.model_dump()
            validation.validate_session_data(data)
            sql_handler.upsert_session(
                self.db_path,
                channel_id,
                data.get("game_type", ""),
                data.get("status", ""),
                str(data.get("host_id", "")),
                data.get("bet_amount", 0),
                data.get("pot", 0),
                data,
            )
        except Exception as e:
            Logger.error("Storage", f"SQLite Save Session Error: {e}", exc_info=True)
            raise StorageError(f"セッション情報の保存に失敗しました: {e}")

    def delete_session(self, channel_id: int) -> None:
        try:
            sql_handler.delete_session(self.db_path, channel_id)
        except Exception as e:
            Logger.error("Storage", f"SQLite Delete Session Error: {e}", exc_info=True)
            raise StorageError(f"セッション情報の削除に失敗しました: {e}")

    def get_all_sessions(self) -> Dict[str, SessionSchemaType]:
        try:
            all_data = sql_handler.get_all_sessions(self.db_path)
            adapter = TypeAdapter(SessionSchemaType)
            res = {}
            for cid, data in all_data.items():
                if "channel_id" not in data:
                    data["channel_id"] = cid
                res[cid] = adapter.validate_python(data)
            return res
        except Exception as e:
            Logger.error("Storage", f"SQLite Get All Sessions Error: {e}", exc_info=True)
            raise StorageError(f"全セッション情報の取得に失敗しました: {e}")


class SQLiteDobumonRepository(SQLiteBaseRepository, IDobumonRepository):
    def get_dobumon(self, dobumon_id: str) -> Optional[DobumonSchema]:
        try:
            data = sql_handler.get_dobumon(self.db_path, dobumon_id)
            return DobumonSchema(**data) if data else None
        except Exception as e:
            Logger.error("Storage", f"SQLite Get Dobumon Error: {e}", exc_info=True)
            raise StorageError(f"怒武者情報の取得に失敗しました: {e}")

    def save_dobumon(self, dobumon: DobumonSchema) -> None:
        try:
            data = dobumon.model_dump()
            validation.validate_dobumon_data(data)
            sql_handler.upsert_dobumon(self.db_path, data)
        except Exception as e:
            if isinstance(e, DataValidationError):
                raise
            Logger.error("Storage", f"SQLite Save Dobumon Error: {e}", exc_info=True)
            raise StorageError(f"怒武者情報の保存に失敗しました: {e}")

    def get_user_dobumons(self, owner_id: int, only_alive: bool = True) -> List[DobumonSchema]:
        try:
            all_data = sql_handler.get_user_dobumons(self.db_path, owner_id, only_alive)
            return [DobumonSchema(**data) for data in all_data]
        except Exception as e:
            Logger.error("Storage", f"SQLite Get User Dobumons Error: {e}", exc_info=True)
            raise StorageError(f"ユーザーの怒武者一覧の取得に失敗しました: {e}")

    def get_dobumons_by_name(self, name: str) -> List[DobumonSchema]:
        try:
            all_data = sql_handler.get_dobumons_by_name(self.db_path, name)
            return [DobumonSchema(**data) for data in all_data]
        except Exception as e:
            Logger.error("Storage", f"SQLite Get Dobumons By Name Error: {e}", exc_info=True)
            raise StorageError(f"名前による怒武者検索に失敗しました: {e}")

    def get_all_alive_dobumons(self) -> List[DobumonSchema]:
        try:
            from core.handlers.sql_handler import dobumon_sql

            all_data = dobumon_sql.get_all_alive_dobumons(self.db_path)
            return [DobumonSchema(**data) for data in all_data]
        except Exception as e:
            Logger.error("Storage", f"SQLite Get All Alive Dobumons Error: {e}", exc_info=True)
            raise StorageError(f"生存している全怒武者の取得に失敗しました: {e}")

    def delete_dobumon(self, dobumon_id: str) -> None:
        try:
            sql_handler.delete_dobumon(self.db_path, dobumon_id)
        except Exception as e:
            Logger.error("Storage", f"SQLite Delete Dobumon Error: {e}", exc_info=True)
            raise StorageError(f"怒武者の削除に失敗しました: {e}")


class SQLiteSystemRepository(SQLiteBaseRepository, ISystemRepository):
    def get_system_data(self, key: str) -> Optional[Dict]:
        try:
            return sql_handler.get_system_stats(self.db_path, key)
        except Exception as e:
            Logger.error("Storage", f"SQLite Get System Data Error: {e}", exc_info=True)
            raise StorageError(f"システムデータの取得に失敗しました: {e}")

    def save_system_data(self, key: str, data: Dict) -> None:
        try:
            sql_handler.upsert_system_stats(self.db_path, key, data)
        except Exception as e:
            Logger.error("Storage", f"SQLite Save System Data Error: {e}", exc_info=True)
            raise StorageError(f"システムデータの保存に失敗しました: {e}")

    def log_jackpot(
        self,
        user_id: int,
        game_type: str,
        hand_name: str,
        rarity: str,
        amount: int,
        pool_after: int,
    ) -> None:
        if user_id < 0:
            return
        try:
            sql_handler.log_jackpot(
                self.db_path, user_id, game_type, hand_name, rarity, amount, pool_after
            )
        except Exception as e:
            Logger.error("Storage", f"SQLite Log Jackpot Error: {e}", exc_info=True)
            raise StorageError(f"ジャックポットログの保存に失敗しました: {e}")


# 過去との互換性のための IStorage は削除 (計画どおり)
