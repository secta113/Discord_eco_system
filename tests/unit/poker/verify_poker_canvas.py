import io
import os
import sys

# プロジェクトルートをパスに追加
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)

from PIL import Image

from logic.poker.pk_canvas import PokerCanvas


def generate_debug_images():
    print("--- Generating Poker Debug Images ---")

    try:
        canvas = PokerCanvas()

        # テストカード (Unicode絵文字に注意)
        community_cards = [("♠", "A"), ("♥", "K"), ("♦", "Q"), ("♣", "J"), ("♠", "10")]
        hole_cards = [("♥", "A"), ("♦", "A")]

        # 1. Table Render
        table_buf = canvas.render_table(community_cards, 1000, "flop")
        os.makedirs("debug", exist_ok=True)
        with open("debug/test_table.png", "wb") as f:
            f.write(table_buf.getbuffer())
        print("Saved debug/test_table.png")

        # 2. Hand Render
        hand_buf = canvas.render_hand(hole_cards)
        with open("debug/test_hand.png", "wb") as f:
            f.write(hand_buf.getbuffer())
        print("Saved debug/test_hand.png")

        # アセットのロード数確認
        print(f"Loaded assets in cache: {len(canvas.cards_cache)}")

    except Exception as e:
        print(f"Error during generation: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    generate_debug_images()
