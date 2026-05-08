import os
import random
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cogs.dobumon import DobumonCog
from core.economy import wallet
from core.handlers import sql_handler
from core.handlers.storage import SQLiteDobumonRepository
from logic.dobumon.core.dob_manager import DobumonManager
from logic.dobumon.core.dob_market_service import DobumonMarketService
from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.core.dob_training_service import DobumonTrainingService
from logic.dobumon.dob_battle.dob_engine import BattleEngine
from logic.dobumon.training import TrainingEngine
from logic.dobumon.ui import (
    DobumonSellView,
    TrainingResultView,
    TrainingView,
)


def setup_test_env(tmp_path):
    db_path = str(tmp_path / "test_play.db")
    sql_handler.init_db(db_path)
    repo = SQLiteDobumonRepository(db_path)
    manager = DobumonManager(repo)
    return manager, repo


def test_dobumon_full_scenario_seeded(tmp_path):
    """【決定論的テスト】シードを固定し、期待通りの育成・戦闘・報酬サイクルを検証"""
    random.seed(42)
    manager, repo = setup_test_env(tmp_path)
    user_id = 2001
    wallet.save_balance(user_id, 10000)

    # 1. 生成
    dobu = manager.create_dobumon(user_id, "固定丸")
    dobu.hp, dobu.atk, dobu.defense, dobu.eva, dobu.spd = 100, 50, 40, 10, 15
    manager.save_dobumon(dobu)

    # 2. 育成 (1回目: 500pts)
    initial_balance = wallet.load_balance(user_id)
    success, res = manager.train_menu(dobu.dobumon_id, "strength")
    assert success is True
    wallet.save_balance(
        user_id, initial_balance - 500
    )  # 本来はServiceが行うがManagerテストなので手動

    # 3. 野生戦
    wild = manager.create_wild_dobumon(dobu)
    # 野生を弱体化させて確実に勝つ
    wild.hp, wild.atk, wild.defense, wild.spd = 10, 5, 5, 5
    engine = BattleEngine(dobu, wild)
    battle_res = engine.simulate()
    assert battle_res["winner_id"] == dobu.dobumon_id

    # 4. 報酬の受け取り
    settlement = manager.settle_wild_battle(battle_res["winner_id"], dobu.dobumon_id, battle_res)
    assert settlement["winner"] == "player"
    wallet.save_balance(user_id, wallet.load_balance(user_id) + settlement["reward"])

    # 最終確認
    final_dobu = manager.get_dobumon(dobu.dobumon_id)
    assert final_dobu.win_count == 1
    # 報酬はランクCベース(10000)だが、属性ボーナス(1.5x)が乗る可能性がある
    actual_balance = wallet.load_balance(user_id)
    expected_no_bonus = 10000 - 500 + 10000
    expected_with_bonus = 10000 - 500 + 15000
    assert actual_balance in [expected_no_bonus, expected_with_bonus]


def test_dobumon_full_scenario_random(tmp_path):
    """【ランダムテスト】シードを固定せず、予期せぬエラーが起きないか検証"""
    manager, storage = setup_test_env(tmp_path)
    user_id = 3001
    wallet.save_balance(user_id, 50000)

    dobu = manager.create_dobumon(user_id, "冒険丸")
    manager.save_dobumon(dobu)

    # 複数回のトレーニング
    for _ in range(3):
        manager.train_menu(dobu.dobumon_id, "running")

    # 野生戦を数回
    for _ in range(2):
        wild = manager.create_wild_dobumon(dobu)
        engine = BattleEngine(dobu, wild)
        battle_res = engine.simulate()
        manager.settle_wild_battle(battle_res["winner_id"], dobu.dobumon_id, battle_res)

    # エラーなく終了することを確認
    assert manager.get_dobumon(dobu.dobumon_id).is_alive == 1


def test_hp_boundary_victory_check(tmp_path):
    """【不具合再発防止】HPが極限（0.1）で勝利した際、表示用データ（steps）が1と記録されるか検証"""
    manager, storage = setup_test_env(tmp_path)
    user_id = 4001

    dobu = manager.create_dobumon(user_id, "不屈丸")
    # HP 0.1, 超高火力
    dobu.hp = 100
    dobu.health = 0.1
    dobu.atk = 9999
    manager.save_dobumon(dobu)

    wild = manager.create_wild_dobumon(dobu)
    wild.hp = 10
    wild.atk = 1
    wild.spd = 1

    # D1が確実に先制するようにSPDを調整
    dobu.spd = 999

    engine = BattleEngine(dobu, wild)
    res = engine.simulate()

    # 最初の行動ステップでHPが1（0.1の切り上げ）になっていることを確認
    # steps[0]は戦闘開始, steps[1]が最初の行動
    assert res["steps"][1]["p1_hp"] == 1
    assert res["winner_id"] == dobu.dobumon_id


def test_economy_and_training_loop(tmp_path):
    """経済システムと育成コストの整合性テスト"""
    manager, storage = setup_test_env(tmp_path)
    user_id = 5001
    wallet.save_balance(user_id, 10000)

    dobu = manager.create_dobumon(user_id, "家計丸")
    manager.save_dobumon(dobu)

    # なつき度を上げる
    dobu.affection = 500  # 50% discount
    manager.save_dobumon(dobu)

    # 本来のコスト計算を模したテスト (DobumonTrainingService相当)
    service = DobumonTrainingService(manager)

    # 1回目 (500 -> 50% discount -> 250)
    cost = TrainingEngine.calculate_training_cost(dobu)
    assert cost == 250

    # 3回トレーニング後のコスト上昇を確認
    from core.utils.time_utils import get_jst_today

    dobu.today_train_count = 3
    dobu.last_train_date = get_jst_today()
    cost_increased = TrainingEngine.calculate_training_cost(dobu)
    # 3回目はベース 4000 -> 50% discount -> 2000
    assert cost_increased == 2000


@pytest.fixture
def cog_dobumon(init_test_env, test_db_path):
    """DobumonCogのテスト用インスタンス。DBパスをテスト用に調整し、バックグラウンドタスクを停止状態で生成。"""
    bot = MagicMock()
    # aging_taskが実行されないようにクラスレベルでパッチ。
    # すでにモジュール読み込み時にデコレータが実行されているため、インスタンス化時のstart()呼び出しを抑制する。
    with patch.object(DobumonCog, "aging_task"):
        cog = DobumonCog(bot)
        # DB一貫性のため、managerのリポジトリパスをテスト用DBに書き換え
        cog.manager.repo.db_path = test_db_path
        return cog


@pytest.mark.asyncio
async def test_sell_command_flow(cog_dobumon, mock_interaction):
    """/dd-dobumon sell の一連の流れ（募集から売却完了まで）をテスト"""
    user_id = mock_interaction.user.id
    manager = cog_dobumon.manager

    # 1. 準備：所持しているドブモンを1体作成
    dobu = manager.create_dobumon(user_id, "テスト丸")
    # 適当なステータスを設定（売却価格に影響）
    dobu.hp, dobu.atk, dobu.defense, dobu.eva, dobu.spd = 100, 100, 100, 100, 100
    dobu.generation = 1
    dobu.affection = 10
    manager.save_dobumon(dobu)

    wallet.save_balance(user_id, 1000)

    # 2. コマンド実行（Cogのメソッドを直接叩く）
    # @app_commands.command でデコレートされたメソッドは .callback を持つ
    await cog_dobumon.sell.callback(cog_dobumon, mock_interaction)

    # 3. Viewが正しく返されたか確認（TypeErrorなどがあればここで落ちる）
    args, kwargs = mock_interaction.followup.send.call_args
    view = kwargs.get("view")
    assert isinstance(view, DobumonSellView)

    # 4. Viewの選択と更新のシミュレーション
    view.selected_dobumon_id = dobu.dobumon_id
    # update_messageを呼び出すことで価格計算ロジックなどを走らせる
    await view.update_message(mock_interaction)

    # 5. 売却確定ボタン押下シミュレーション
    await view._on_sell_click(mock_interaction)

    # 6. 結果の検証
    # DBにアーカイブされていること (is_sold=True)
    sold_dobu = manager.get_dobumon(dobu.dobumon_id)
    assert sold_dobu is not None
    assert sold_dobu.is_sold
    assert not sold_dobu.is_alive

    # ポイントが増えていること (1000 + 23888 = 24888)
    final_balance = wallet.load_balance(user_id)
    assert final_balance == 24888


@pytest.mark.asyncio
async def test_sell_unauthorized_flow(cog_dobumon, mock_interaction):
    """他人の怒武者を売却しようとした場合にエラーになることを検証"""
    owner_id = 999
    other_user_id = mock_interaction.user.id  # 123456789
    manager = cog_dobumon.manager

    # 他人のドブモンを作成
    dobu = manager.create_dobumon(owner_id, "他人丸")
    manager.save_dobumon(dobu)

    # 他人(123456789)として売却を実行 -> DobumonNotFoundError を期待
    from logic.dobumon.core.dob_exceptions import DobumonNotFoundError

    with pytest.raises(DobumonNotFoundError):
        await cog_dobumon.market_service.execute_sell(mock_interaction, dobu.dobumon_id)


@pytest.mark.asyncio
async def test_buy_limit_flow(cog_dobumon, mock_interaction):
    """購入制限（8体まで）が正しく機能するか検証"""
    user_id = mock_interaction.user.id
    manager = cog_dobumon.manager
    wallet.save_balance(user_id, 200000)  # 十分な資金

    from logic.dobumon.core.dob_constants import MAX_DOBUMON_POSSESSION

    # 上限まで作成
    for i in range(MAX_DOBUMON_POSSESSION):
        d = manager.create_dobumon(user_id, f"所持丸_{i}")
        manager.save_dobumon(d)

    # 上限超えの購入を試みる -> DobumonError を期待
    from logic.dobumon.core.dob_exceptions import DobumonError

    with pytest.raises(
        DobumonError, match=f"既に {MAX_DOBUMON_POSSESSION} 体の怒武者を所持しています"
    ):
        # Cogのbuyコマンドを直接呼び出し
        await cog_dobumon.buy.callback(cog_dobumon, mock_interaction)


@pytest.mark.asyncio
async def test_wild_battle_death_flow(cog_dobumon, mock_interaction):
    """野生戦での敗北による死亡（ロスト）フローを検証"""
    user_id = mock_interaction.user.id
    manager = cog_dobumon.manager

    # 準備：激弱ドブモン
    dobu = manager.create_dobumon(user_id, "儚い丸")
    dobu.hp, dobu.atk, dobu.defense, dobu.spd = 1, 1, 1, 1
    manager.save_dobumon(dobu)

    # 敗北シミュレーションデータ作成
    battle_res = {
        "winner_id": "WILD_ID",  # 野生の勝利
        "steps": [],
        "p1_after_hp": 0,
        "p2_after_hp": 100,
    }

    # 精算処理（敗北時）
    # Service を通さず Manager を直接叩いて内部状態の変化を確認
    # DISABLE_DEATH を強制的に False にして死亡を発生させる
    with patch("logic.dobumon.core.dob_manager.DISABLE_DEATH", False):
        res = manager.settle_wild_battle("WILD_ID", dobu.dobumon_id, battle_res)

    assert res["winner"] == "wild"
    # 生存フラグが折れていることを確認
    updated_model = manager.repo.get_dobumon(dobu.dobumon_id)
    assert updated_model.is_alive == 0
    # manager経由でも False になっているはず
    updated_dobu = manager.get_dobumon(dobu.dobumon_id)
    assert not updated_dobu.is_alive


@pytest.mark.asyncio
async def test_training_flow_completion(cog_dobumon, mock_interaction):
    """トレーニングの開始から完了、継続ボタンによる再開までのフローをテスト"""
    user_id = mock_interaction.user.id
    manager = cog_dobumon.manager
    service = cog_dobumon.training_service

    # 1. 準備：怒武者を作成
    dobu = manager.create_dobumon(user_id, "特訓丸")
    dobu.hp, dobu.atk, dobu.defense, dobu.eva, dobu.spd = 100, 50, 50, 10, 10
    manager.save_dobumon(dobu)
    wallet.save_balance(user_id, 10000)

    # 2. コマンド実行（トレーニングウィザード表示）
    await cog_dobumon.train.callback(cog_dobumon, mock_interaction)

    # 3. TrainingView が返されたか確認
    args, kwargs = mock_interaction.followup.send.call_args
    view = kwargs.get("view")
    assert isinstance(view, TrainingView)

    # 4. 個体とメニューを選択して開始
    view.selected_dobumon_id = dobu.dobumon_id
    view.selected_menu = "strength"
    # クラス側の関数を取得して呼び出す
    await TrainingView.start_button(view, mock_interaction, view.start_button)

    # 5. トレーニング実行（DobumonTrainingService.execute_training が呼ばれる）
    # 結果として TrainingResultView がセットされたメッセージが送信されるはず
    args, kwargs = mock_interaction.edit_original_response.call_args
    result_view = kwargs.get("view")
    assert isinstance(result_view, TrainingResultView)

    # 6. 「続けてトレーニングする」ボタン押下シミュレーション
    await TrainingResultView.continue_training(
        result_view, mock_interaction, result_view.continue_training
    )

    # 7. 元のボタンが無効化されたか確認 (edit_message)
    args, kwargs = mock_interaction.response.edit_message.call_args
    edited_view = kwargs.get("view")
    assert all(item.disabled for item in edited_view.children if hasattr(item, "disabled"))

    # 8. 新しい TrainingView がフォローアップ経由でエフェメラル送信されたか確認
    args, kwargs = mock_interaction.followup.send.call_args
    new_train_view = kwargs.get("view")
    assert isinstance(new_train_view, TrainingView)
    # 前回と同じ個体が初期選択されていること
    assert new_train_view.selected_dobumon_id == dobu.dobumon_id
    # エフェメラル設定であること
    assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_training_result_show_status(cog_dobumon, mock_interaction):
    """トレーニング完了後の「ステータスを表示」ボタンの挙動をテスト"""
    user_id = mock_interaction.user.id
    manager = cog_dobumon.manager
    service = cog_dobumon.training_service

    # 1. 準備：怒武者を作成
    dobu = manager.create_dobumon(user_id, "ステータス確認丸")
    manager.save_dobumon(dobu)

    # 2. TrainingResultView を作成
    result_view = TrainingResultView(mock_interaction.user, manager, service, dobu.dobumon_id)

    # 3. 「ステータスを表示」ボタン押下シミュレーション
    await TrainingResultView.show_status(result_view, mock_interaction, result_view.show_status)

    # 4. ステータスがエフェメラルで送信されたか確認
    args, kwargs = mock_interaction.response.send_message.call_args
    assert kwargs.get("ephemeral") is True
    embed = kwargs.get("embed")
    assert embed.title == f"📊 {dobu.name} の現在の能力"

    # 5. ボタンが無効化されていないことを確認
    assert all(not item.disabled for item in result_view.children if hasattr(item, "disabled"))
