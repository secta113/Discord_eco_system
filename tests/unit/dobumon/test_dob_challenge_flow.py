from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from logic.dobumon.core.dob_battle_service import DobumonBattleService
from logic.dobumon.core.dob_models import Dobumon


class MockMember:
    def __init__(self, id, name):
        self.id = id
        self.display_name = name
        self.mention = f"<@{id}>"


@pytest.mark.asyncio
async def test_execute_challenge_sends_view():
    """挑戦申し込み時に ChallengeView が送信されることを検証"""
    manager = MagicMock()
    service = DobumonBattleService(manager)

    # 攻撃者
    attacker = Dobumon(
        dobumon_id="atk_id",
        owner_id=100,
        name="Atk",
        gender="M",
        hp=100,
        atk=50,
        defense=50,
        eva=10,
        spd=10,
    )
    manager.get_dobumon.return_value = attacker
    # 攻撃者のリスト返却
    manager.get_user_dobumons.side_effect = lambda uid, only_alive: (
        [attacker] if uid == 100 else [defender]
    )

    # 防衛者
    defender = Dobumon(
        dobumon_id="def_id",
        owner_id=200,
        name="Def",
        gender="F",
        hp=100,
        atk=50,
        defense=50,
        eva=10,
        spd=10,
    )

    interaction = AsyncMock()
    interaction.user.id = 100
    interaction.user.display_name = "UserA"

    target = MockMember(200, "UserB")

    # ウィザードの第1段階をスキップして、直接execute_challengeを呼び出すテストにするか、
    # あるいは execute_challenge (ウィザード開始) をテストするか。
    # サービス側では execute_challenge がウィザード開始になったので、それに合わせる。
    await service.execute_challenge(interaction, target)

    # Followup.send が呼ばれ、DobumonSelectionView が渡されていること
    interaction.followup.send.assert_called_once()
    args, kwargs = interaction.followup.send.call_args
    assert "view" in kwargs
    from logic.dobumon.ui.dob_battle import DobumonSelectionView

    assert isinstance(kwargs["view"], DobumonSelectionView)


@pytest.mark.asyncio
async def test_start_challenge_battle_creates_session():
    """個体確定後にバトルセッションが作成されることを検証"""
    manager = MagicMock()
    service = DobumonBattleService(manager)

    attacker = Dobumon(
        dobumon_id="atk_id",
        owner_id=100,
        name="Atk",
        gender="M",
        hp=100,
        atk=50,
        defense=50,
        eva=10,
        spd=10,
    )
    defender = Dobumon(
        dobumon_id="def_id",
        owner_id=200,
        name="Def",
        gender="F",
        hp=100,
        atk=50,
        defense=50,
        eva=10,
        spd=10,
    )

    manager.get_dobumon.return_value = defender

    # discord.Interaction のモックをより正確に作成
    interaction = MagicMock(spec=discord.Interaction)
    interaction.response = MagicMock(spec=discord.InteractionResponse)
    interaction.response.is_done.return_value = False
    interaction.response.send_message = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.channel_id = 12345

    attacker_user = MagicMock()
    attacker_user.id = 100

    with (
        patch("logic.dobumon.core.dob_battle_service.game_manager") as mock_game_manager,
        patch("logic.dobumon.core.dob_battle_service.BattleEngine") as mock_engine,
        patch("logic.dobumon.core.dob_battle_service.BattleAutoView") as mock_battle_view,
    ):
        mock_engine.return_value.simulate.return_value = {
            "steps": [],
            "winner_id": "atk_id",
            "loser_id": "def_id",
        }
        mock_game_manager.create_dobumon_battle.return_value = (MagicMock(), "success")
        mock_battle_view.return_value.start = AsyncMock()
        mock_battle_view.return_value.create_embed.return_value = MagicMock()

        await service.start_challenge_battle(
            interaction, attacker_user, attacker, defender.dobumon_id
        )

        # セッション作成が呼ばれたか
        mock_game_manager.create_dobumon_battle.assert_called_once()
        # メッセージが送信されたか
        interaction.response.send_message.assert_called_once()
        # start() が呼ばれたか
        mock_battle_view.return_value.start.assert_called_once()


@pytest.mark.asyncio
async def test_challenge_acceptance_flow_single_dobumon():
    """防衛者が1体のみ所持の場合、受諾で即座に開始されることを検証"""
    from logic.dobumon.ui.dob_battle import ChallengeView

    manager = MagicMock()
    callback = AsyncMock()
    attacker = Dobumon(
        dobumon_id="atk_id",
        owner_id=100,
        name="Atk",
        gender="M",
        hp=100,
        atk=50,
        defense=50,
        eva=10,
        spd=10,
    )
    attacker_user = MagicMock(id=100)
    target_user = MagicMock(id=200)

    # 防衛者の所持ドブモンは1体
    defender = Dobumon(
        dobumon_id="def_id",
        owner_id=200,
        name="Def",
        gender="F",
        hp=100,
        atk=50,
        defense=50,
        eva=10,
        spd=10,
    )
    manager.get_user_dobumons.return_value = [defender]

    view = ChallengeView(attacker, attacker_user, target_user, manager, callback)

    interaction = MagicMock(spec=discord.Interaction)
    interaction.user.id = 200
    interaction.response = MagicMock(spec=discord.InteractionResponse)
    interaction.response.edit_message = AsyncMock()
    interaction.followup = AsyncMock()

    # 直接メソッドを呼ぶ (discord.py の _ItemCallback は bind 時に (interaction) のみ期待する場合がある)
    await view.accept.callback(interaction)

    # コールバック（バトル開始）が即座に呼ばれたか
    callback.assert_called_once_with(interaction, attacker_user, attacker, defender.dobumon_id)


@pytest.mark.asyncio
async def test_challenge_acceptance_flow_multiple_dobumons():
    """防衛者が複数所持の場合、受諾で選択ビューが表示されることを検証"""
    from logic.dobumon.ui.dob_battle import ChallengeView

    manager = MagicMock()
    callback = AsyncMock()
    attacker = Dobumon(
        dobumon_id="atk_id",
        owner_id=100,
        name="Atk",
        gender="M",
        hp=100,
        atk=50,
        defense=50,
        eva=10,
        spd=10,
    )
    attacker_user = MagicMock(id=100)
    target_user = MagicMock(id=200)

    # 防衛者の所持ドブモンは2体
    def1 = Dobumon(
        dobumon_id="def1",
        owner_id=200,
        name="Def1",
        gender="F",
        hp=100,
        atk=50,
        defense=50,
        eva=10,
        spd=10,
    )
    def2 = Dobumon(
        dobumon_id="def2",
        owner_id=200,
        name="Def2",
        gender="F",
        hp=100,
        atk=50,
        defense=50,
        eva=10,
        spd=10,
    )
    manager.get_user_dobumons.return_value = [def1, def2]

    view = ChallengeView(attacker, attacker_user, target_user, manager, callback)

    interaction = MagicMock(spec=discord.Interaction)
    interaction.user.id = 200
    interaction.response = MagicMock(spec=discord.InteractionResponse)
    interaction.response.edit_message = AsyncMock()
    interaction.followup = AsyncMock()

    # 受諾ボタンシミュレーション
    await view.accept.callback(interaction)

    # コールバック（バトル開始）はまだ呼ばれない
    callback.assert_not_called()
    # 選択メニューが送信されたか確認
    interaction.followup.send.assert_called_once()
    args, kwargs = interaction.followup.send.call_args
    from logic.dobumon.ui.dob_battle import DobumonSelectionView

    assert isinstance(kwargs["view"], DobumonSelectionView)
