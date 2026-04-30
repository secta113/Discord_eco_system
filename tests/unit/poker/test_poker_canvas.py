import io

from logic.poker.pk_canvas import PokerCanvas


def test_poker_canvas_render():
    """PokerCanvasが例外なく画像を生成し、サイズが正しいことを検証"""
    canvas = PokerCanvas()
    community_cards = [("♠", "A"), ("♥", "K"), ("♦", "Q")]
    pot_amount = 10000
    phase_name = "flop"

    img_buf = canvas.render_table(community_cards, pot_amount, phase_name)

    assert isinstance(img_buf, io.BytesIO)
    assert img_buf.getbuffer().nbytes > 0


def test_poker_canvas_empty_cards():
    """カードが空の場合でもレンダリングできることを検証"""
    canvas = PokerCanvas()
    img_buf = canvas.render_table([], 0, "pre_flop")
    assert img_buf.getbuffer().nbytes > 0


def test_poker_canvas_full_cards():
    """5枚すべてのカードがある場合を検証"""
    canvas = PokerCanvas()
    cards = [("♠", "10"), ("♣", "J"), ("♦", "Q"), ("♥", "K"), ("♠", "A")]
    img_buf = canvas.render_table(cards, 99999, "river")
    assert img_buf.getbuffer().nbytes > 0


def test_poker_canvas_render_hand():
    """手札（ホールカード）2枚の画像生成を検証"""
    canvas = PokerCanvas()
    hole_cards = [("♠", "A"), ("♥", "A")]
    img_buf = canvas.render_hand(hole_cards)
    assert isinstance(img_buf, io.BytesIO)
    assert img_buf.getbuffer().nbytes > 0
