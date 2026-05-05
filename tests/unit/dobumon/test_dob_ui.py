import pytest

from logic.dobumon.core.dob_formatter import DobumonFormatter
from logic.dobumon.core.dob_models import Dobumon


def test_vague_gains():
    """情緒的な成長表現のテスト"""
    test_cases = [
        (0.1, "微かな手応えを感じた"),
        (0.6, "少し成長したようだ"),
        (1.5, "確かな手応えを感じている"),
        (3.0, "目覚ましい成長を遂げた！"),
        (-0.1, "僅かに精彩を欠いた"),
        (-0.5, "少し鈍ったようだ"),
        (-1.5, "ガタがきているようだ..."),
        (0.0, "変化はなかった"),
    ]
    for val, expected in test_cases:
        actual = DobumonFormatter.get_vague_gain_text(val)
        assert actual == expected


def test_privacy_obfuscation():
    """所有者以外に対するステータス秘匿のテスト"""
    dobu = Dobumon(
        dobumon_id="id",
        owner_id=1,
        name="SecretMonster",
        gender="M",
        hp=100.0,
        atk=50.0,
        defense=50.0,
        eva=10.0,
        spd=20.0,
        affection=100,
    )

    # 所有者視点: 数値が見えること
    owner_grid = DobumonFormatter.get_stat_grid(dobu, is_owner=True)
    assert "50" in owner_grid
    assert "100" in owner_grid

    # 非所有者視点: 数値が ??? になっていること
    guest_grid = DobumonFormatter.get_stat_grid(dobu, is_owner=False)
    assert "50" not in guest_grid
    assert "???" in guest_grid
    assert "100" not in guest_grid

    # Status Embed の秘匿
    guest_embed = DobumonFormatter.format_status_embed(dobu, is_owner=False)
    assert "???" in guest_embed.description
    assert "分かりません" in guest_embed.description


def test_hp_bar_privacy():
    """HPバーの秘匿テスト"""
    # 所有者: 数値あり
    bar_owner = DobumonFormatter.get_hp_bar(50, 100, is_owner=True)
    assert "50 / 100" in bar_owner

    # 非所有者: 数値なし
    bar_guest = DobumonFormatter.get_hp_bar(50, 100, is_owner=False)
    assert "??? / ???" in bar_guest


def test_bond_text_formatting():
    """なつき度（絆）のUIメッセージフォーマットのテスト"""
    test_cases = [
        (-10, "🥀"),
        (0, "🍂"),
        (4, "🍂"),
        (5, "🌱"),
        (14, "🌱"),
        (15, "💖"),
        (29, "💖"),
        (30, "✨"),
        (49, "✨"),
        (50, "🤝"),
        (69, "🤝"),
        (70, "🔥"),
        (99, "🔥"),
        (100, "💎"),
        (150, "💎"),
    ]
    for val, expected_icon in test_cases:
        actual = DobumonFormatter.get_bond_text(val)
        assert expected_icon in actual
