import asyncio
import io
import os
import sys
from unittest.mock import MagicMock

# プロジェクトルートをパスに追加
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)

from logic.blackjack.bj_canvas import BlackjackCanvas
from logic.blackjack.bj_deck import Deck
from logic.blackjack.bj_service import BlackjackService


async def test_bj_ui_generation():
    print("--- Testing Blackjack UI Generation ---")

    # 擬似的なセッション作成
    session = BlackjackService(channel_id=123, bet_amount=100)

    # プレイヤー追加 (Userオブジェクトを模倣)
    session.add_player(MagicMock(id=456, display_name="Alice", mention="<@456>"), "Alice")
    session.add_player(MagicMock(id=789, display_name="Bob", mention="<@789>"), "Bob")

    # ゲーム開始相当の状態にする
    session.start_game()

    # キャンバスとViewの挙動をテスト (ViewはDiscord.py依存が強いので主要ロジックのみ)
    canvas = BlackjackCanvas()

    # 1. Dealer image test
    d_img = canvas.render_hand(session.dealer_hand, hide_first=True)
    os.makedirs("debug", exist_ok=True)
    with open("debug/bj_dealer_hidden.png", "wb") as f:
        f.write(d_img.getbuffer())
    print("Saved debug/bj_dealer_hidden.png")

    # 2. Player images test (with Split)
    for p_info in session.players:
        uid = p_info["id"]
        player = session.player_states[uid]

        # もしAliceなら手動でスプリット状態にする
        hands_to_render = [h.cards for h in player.hands]
        if p_info["name"] == "Alice":
            # 2手札目を追加
            hands_to_render.append([("♥", "7"), ("♣", "8")])
            print("Testing split hand for Alice")

        p_img = canvas.render_split_hands(hands_to_render)
        with open(f"debug/bj_player_{uid}_split.png", "wb") as f:
            f.write(p_img.getbuffer())
        print(f"Saved debug/bj_player_{uid}_split.png")

    print("\nUI Test Complete.")


if __name__ == "__main__":
    asyncio.run(test_bj_ui_generation())
