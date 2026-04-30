import io
from typing import List, Tuple

from PIL import Image

from core.utils.card_assets import CardAssetManager


class BlackjackCanvas:
    """
    ブラックジャックのカード画像を合成するクラス。
    ポーカーと共通のカードアセット (data/card/) を使用する。
    """

    CARD_WIDTH = 150
    CARD_HEIGHT = 220
    OVERLAP = 40  # カードを重ねる量（ピクセル）

    def __init__(self):
        # CardAssetManagerを初期化（ロード）
        CardAssetManager.get_assets()

    def render_hand(self, cards: List[Tuple[str, str]], hide_first: bool = False) -> io.BytesIO:
        """
        手札画像を合成する（単一の手札用）。
        hide_first=True の場合、1枚目を裏返しにする（ディーラー用）。
        """
        return self.render_split_hands([cards], hide_first=hide_first)

    def render_split_hands(
        self, hands: List[List[Tuple[str, str]]], hide_first: bool = False
    ) -> io.BytesIO:
        """
        複数の手札を垂直方向に並べて合成する。
        """
        if not hands:
            hands = [[None]]

        v_gap = 30  # 手札間の垂直方向の隙間
        max_cards = max(len(h) for h in hands)

        # キャンバスサイズの計算
        width = self.CARD_WIDTH + (self.CARD_WIDTH - self.OVERLAP) * (max_cards - 1)
        total_height = (self.CARD_HEIGHT * len(hands)) + (v_gap * (len(hands) - 1))

        # 透明なキャンバス作成
        img = Image.new("RGBA", (int(width), int(total_height)), (0, 0, 0, 0))

        for h_idx, cards in enumerate(hands):
            y_offset = h_idx * (self.CARD_HEIGHT + v_gap)

            for i, card in enumerate(cards):
                x = int((self.CARD_WIDTH - self.OVERLAP) * i)
                y = y_offset

                if h_idx == 0 and i == 0 and hide_first:
                    card_img = CardAssetManager.get_image("card_back")
                else:
                    card_img = self._get_card_image(card)

                if card_img:
                    img.paste(card_img, (x, y), card_img)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf

    def _get_card_image(self, card_tuple):
        """カードタプル (suit, rank) から画像を返す"""
        if not card_tuple:
            return CardAssetManager.get_image("card_back")

        suit_sym, rank = card_tuple
        # ファイル名規則に合わせて変換
        suit_mapping = {"♠": "S", "♥": "H", "♦": "D", "♣": "C", "Joker": "joker"}

        if suit_sym == "Joker":
            return CardAssetManager.get_image("joker")

        s_let = suit_mapping.get(suit_sym, "S")
        key = f"{s_let}_{rank}"
        return CardAssetManager.get_image(key)
