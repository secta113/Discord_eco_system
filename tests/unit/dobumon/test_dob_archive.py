import json
from unittest.mock import MagicMock

import pytest

from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.dob_views.dob_kinship_tree import DobumonKinshipTree


def test_canvas_ancestor_auto_completion():
    """
    リポジトリが渡された場合、Canvasが欠損した祖先データを自動取得することを検証します。
    """
    # 1. 準備: 所持している子個体
    child = Dobumon(
        dobumon_id="child_id",
        owner_id=123,
        name="Child",
        gender="M",
        hp=100,
        atk=100,
        defense=100,
        eva=100,
        spd=100,
        generation=2,
        lineage=["parent_id|1|f"],
    )

    # 2. 準備: アーカイブされている親個体のデータ (リポジトリが返す想定)
    parent_data = {
        "dobumon_id": "parent_id",
        "owner_id": "123",
        "name": "ArchivedParent",
        "gender": "F",
        "hp": 150,
        "atk": 150,
        "defense": 150,
        "eva": 150,
        "spd": 150,
        "is_alive": False,
        "is_sold": True,
        "generation": 1,
        "lineage": [],
        "skills": [],
        "iv": {},
        "genetics": {},
    }

    # リポジトリのモック
    mock_repo = MagicMock()
    # get_dobumon が Pydantic スキーマに近いオブジェクト（または to_dict を持つもの）を返すように設定
    mock_schema = MagicMock()
    mock_schema.to_dict.return_value = parent_data
    mock_schema.model_dump.return_value = parent_data
    mock_repo.get_dobumon.return_value = mock_schema

    # 3. 実行: Canvas レンダリング
    canvas = DobumonKinshipTree()
    # 実際には画像が生成されるが、内部で repo.get_dobumon が呼ばれたことを確認したい
    # io.BytesIO を返すので、中身までは検証せず呼び出しのみ確認
    canvas.render_pedigree_map("TestUser", [child], owner_id=123, repo=mock_repo)

    # 4. 検証: 親IDでリポジトリに問い合わせが行われたか
    mock_repo.get_dobumon.assert_called_with("parent_id")


def test_dobumon_model_sell_state():
    """
    Dobumonモデルのsell()メソッドが正しく状態を遷移させることを検証します。
    """
    dobu = Dobumon(
        dobumon_id="test_id",
        owner_id=123,
        name="Test",
        gender="M",
        hp=100,
        atk=100,
        defense=100,
        eva=100,
        spd=100,
        is_alive=True,
        is_sold=False,
    )

    dobu.sell()

    assert dobu.is_alive is False
    assert dobu.is_sold is True
    assert dobu.health == 0.0
