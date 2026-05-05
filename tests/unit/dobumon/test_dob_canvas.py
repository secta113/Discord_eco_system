import io

import pytest

from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.ui.dob_kinship_tree import DobumonKinshipTree


def test_dobumon_canvas_render_pedigree_smoke():
    """家系図形式の描画が例外なく完了し、BytesIOが返ってくるかのスモークテスト"""
    canvas = DobumonKinshipTree()

    # ダミーデータ：親子関係を持たせる
    # parent1 (Gen 1) -> child1 (Gen 2)
    # parent2 (Gen 1) -> child1 (Gen 2)
    # child1 (Gen 2) -> grandchild (Gen 3)

    p1 = Dobumon(
        dobumon_id="p1",
        owner_id=1,
        name="Parent 1",
        gender="M",
        hp=100,
        atk=50,
        defense=50,
        eva=50,
        spd=50,
        attribute="fire",
        generation=1,
        max_lifespan=100,
        lifespan=80,
        lineage=[],
    )
    p2 = Dobumon(
        dobumon_id="p2",
        owner_id=1,
        name="Parent 2",
        gender="F",
        hp=100,
        atk=50,
        defense=50,
        eva=50,
        spd=50,
        attribute="water",
        generation=1,
        max_lifespan=100,
        lifespan=80,
        lineage=[],
    )
    c1 = Dobumon(
        dobumon_id="c1",
        owner_id=1,
        name="Child 1",
        gender="M",
        hp=100,
        atk=50,
        defense=50,
        eva=50,
        spd=50,
        attribute="grass",
        generation=2,
        max_lifespan=100,
        lifespan=80,
        lineage=["p1|1|0.0", "p2|1|0.0"],
    )
    gc1 = Dobumon(
        dobumon_id="gc1",
        owner_id=1,
        name="GrandChild 1",
        gender="F",
        hp=100,
        atk=50,
        defense=50,
        eva=50,
        spd=50,
        attribute="fire",
        generation=3,
        max_lifespan=100,
        lifespan=80,
        lineage=["c1|1|0.0", "p1|2|0.0", "p2|2|0.0"],
    )

    # 実際には所持しているのは c1 と gc1 だけ（p1, p2 は売却済み）というケース
    current_list = [c1, gc1]

    buf = canvas.render_pedigree_map("Tester", current_list, owner_id=1)

    assert isinstance(buf, io.BytesIO)
    assert buf.getbuffer().nbytes > 0


def test_dobumon_canvas_pedigree_empty():
    """所持数0の場合のレンダリングテスト"""
    canvas = DobumonKinshipTree()
    buf = canvas.render_pedigree_map("EmptyPlayer", [], owner_id=1)

    assert isinstance(buf, io.BytesIO)
    assert buf.getbuffer().nbytes > 0
