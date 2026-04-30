import datetime
from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from core.utils.exceptions import DataValidationError


class UserSchema(BaseModel):
    """ユーザー用データベーススキーマ"""

    model_config = ConfigDict(extra="forbid")

    id: int
    balance: int = Field(ge=0, description="所持ポイント。0以上である必要があります。")
    last_daily: Optional[str] = Field(default="1970-01-01", pattern=r"^\d{4}-\d{2}-\d{2}$")
    last_gacha_daily: Optional[str] = Field(default="1970-01-01", pattern=r"^\d{4}-\d{2}-\d{2}$")
    gacha_collection: List[int] = Field(default_factory=list)
    history: List[Dict[str, Any]] = Field(default_factory=list)
    total_wins: int = Field(default=0, ge=0)
    games_played: int = Field(default=0, ge=0)
    max_win_amount: int = Field(default=0, ge=0)
    gacha_count_today: int = Field(default=0, ge=0, le=3)
    last_wild_battle_date: Optional[str] = Field(
        default="1970-01-01", pattern=r"^\d{4}-\d{2}-\d{2}$"
    )
    wild_battle_count_today: int = Field(default=0, ge=0)
    dob_buy_data: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("last_daily", "last_gacha_daily")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        if v is None:
            return v
        try:
            datetime.datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"日付形式が不正です (YYYY-MM-DD): {v}")
        return v


# --- ゲームセッション用スキーマ (ポリモーフィック) ---


class BaseSessionSchema(BaseModel):
    """全ゲーム共通の基本項目"""

    model_config = ConfigDict(extra="forbid")

    channel_id: Union[int, str]
    bet_amount: int = Field(default=0, ge=0)
    status: str = Field(pattern=r"^(recruiting|playing|settled|cancelled)$")
    pot: int = Field(default=0, ge=0)
    players: List[Dict[str, Any]] = Field(default_factory=list)
    turn_index: int = Field(default=0, ge=0)
    host_id: Union[int, str] = Field(default=0)
    updated_at: Optional[str] = None

    @field_validator("channel_id", "host_id", mode="before")
    @classmethod
    def coerce_id_to_str(cls, v: Any) -> Any:
        if v is None:
            return v
        return str(v)


class ChinchiroSessionSchema(BaseSessionSchema):
    game_type: Literal["chinchiro"]
    player_states: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    current_roll_count: int = Field(default=0, ge=0)


class BlackjackSessionSchema(BaseSessionSchema):
    game_type: Literal["blackjack"]
    deck: Dict[str, Any]
    dealer_hand: List[Any] = Field(default_factory=list)
    player_states: Dict[str, Any] = Field(default_factory=dict)
    is_dealer_turn_executed: bool = Field(default=False)


class PokerSessionSchema(BaseSessionSchema):
    game_type: Literal["poker"]
    buyin_amount: int = Field(ge=0)
    deck: Dict[str, Any]
    community_cards: List[Any] = Field(default_factory=list)
    player_states: Dict[str, Any] = Field(default_factory=dict)
    phase: str
    current_max_bet: int = Field(default=0, ge=0)
    button_index: int = Field(default=0, ge=0)
    table_average_stack: float = Field(default=0.0)
    target_player_count: int = Field(default=4)
    game_rank: str = "common"
    npc_blueprints: List[Dict[str, Any]] = Field(default_factory=list)


class MatchSessionSchema(BaseSessionSchema):
    game_type: Literal["match"]


class DobumonBattleSessionSchema(BaseSessionSchema):
    game_type: Literal["dobumon_battle"]
    attacker_data: Dict[str, Any]
    defender_data: Dict[str, Any]
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    winner_id: Optional[str] = None
    loser_id: Optional[str] = None
    battle_type: str = "challenge"


# 判別子(game_type)に基づいた統合スキーマ
SessionSchemaType = Annotated[
    Union[
        ChinchiroSessionSchema,
        BlackjackSessionSchema,
        PokerSessionSchema,
        MatchSessionSchema,
        DobumonBattleSessionSchema,
    ],
    Field(discriminator="game_type"),
]


class DobumonSchema(BaseModel):
    """怒武者用データベーススキーマ"""

    model_config = ConfigDict(extra="forbid")

    dobumon_id: str
    owner_id: str
    name: str = Field(min_length=1, max_length=20)
    gender: str = Field(pattern=r"^[MF]$")

    @field_validator("owner_id", "dobumon_id", mode="before")
    @classmethod
    def coerce_to_str(cls, v: Any) -> Any:
        if v is None:
            return v
        return str(v)

    hp: float = Field(ge=0)
    atk: float = Field(ge=0)
    defense: float = Field(ge=0)
    eva: float = Field(ge=0)
    spd: float = Field(ge=0)
    health: float = Field(default=100.0, ge=0)
    skills: List[Dict[str, Any]] = Field(default_factory=list)
    iv: Dict[str, float] = Field(default_factory=dict)
    lifespan: float = Field(default=100.0, ge=0)
    is_alive: int = Field(default=1, le=1, ge=0)
    attribute: Optional[str] = Field(default="")
    affection: int = Field(default=0, ge=0)
    genetics: Dict[str, Any] = Field(default_factory=dict)
    win_count: int = Field(default=0, ge=0)
    rank: int = Field(default=0, ge=0)
    generation: int = Field(default=1, ge=1)
    last_train_date: Optional[str] = Field(default="1970-01-01", pattern=r"^\d{4}-\d{2}-\d{2}$")
    today_train_count: int = Field(default=0, ge=0)
    today_wild_battle_count: int = Field(default=0, ge=0)
    # 追加属性 (v2.4+)
    is_sterile: bool = Field(default=False)
    illness_rate: float = Field(default=0.01, ge=0)
    can_extend_lifespan: bool = Field(default=True)
    max_lifespan: float = Field(default=100.0, ge=0)
    today_affection_gain: int = Field(default=0, ge=0)
    today_massage_count: int = Field(default=0, ge=0)
    lineage: List[str] = Field(default_factory=list)
    traits: List[str] = Field(default_factory=list)
    shop_flags: Dict[str, Any] = Field(default_factory=dict)
    is_sold: int = Field(default=0, ge=0, le=1)

    created_at: Optional[str] = ""
    updated_at: Optional[str] = ""


def validate_user_data(data: dict) -> None:
    """
    DB保存前のユーザーデータの形式と値の妥当性を検証します。
    """
    try:
        UserSchema(**data)
    except ValidationError as e:
        errors = e.errors()
        msg = "; ".join(
            [f"{err['loc'][-1] if err['loc'] else 'root'}: {err['msg']}" for err in errors]
        )
        raise DataValidationError(f"ユーザーデータの検証に失敗しました: {msg}")


def validate_session_data(data: dict) -> None:
    """
    DB保存前のゲームセッションデータの形式と必須項目を検証します。
    ポリモーフィックなスキーマを適用します。
    """
    from pydantic import TypeAdapter

    adapter = TypeAdapter(SessionSchemaType)
    try:
        adapter.validate_python(data)
    except ValidationError as e:
        errors = e.errors()
        msg = "; ".join(
            [f"{err['loc'][-1] if err['loc'] else 'root'}: {err['msg']}" for err in errors]
        )
        raise DataValidationError(f"セッションデータの検証に失敗しました: {msg}")


def validate_dobumon_data(data: dict) -> None:
    """
    DB保存前の怒武者データの形式と妥当性を検証します。
    """
    try:
        DobumonSchema(**data)
    except ValidationError as e:
        errors = e.errors()
        msg = "; ".join(
            [f"{err['loc'][-1] if err['loc'] else 'root'}: {err['msg']}" for err in errors]
        )
        raise DataValidationError(f"怒武者データの検証に失敗しました: {msg}")
