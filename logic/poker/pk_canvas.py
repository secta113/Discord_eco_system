import io
from typing import List, Tuple

from PIL import Image

from core.utils.card_assets import CardAssetManager


class PokerCanvas:
    """
    ポーカーの画像を高速に合成・配信することに特化したクラス。
    アセットをメモリにプリロードし、フォントレンダリングを廃止することで爆速化。
    """

    TABLE_COLOR = (31, 139, 76)  # Dark Green (0x1F8B4C)

    # カードの表示サイズ
    CARD_WIDTH = 150
    CARD_HEIGHT = 220
    SPACING = 20

    def __init__(self):
        # CardAssetManagerを初期化（ロード）
        CardAssetManager.get_assets()
        self._base_table = self._precompute_base_table()

    def _precompute_base_table(self) -> Image.Image:
        """5枚の裏面カードが並んだベース画像を生成・キャッシュする。"""
        width, height = 850, 300
        img = Image.new("RGBA", (width, height), self.TABLE_COLOR)

        total_cards_width = (self.CARD_WIDTH * 5) + (self.SPACING * 4)
        start_x = (width - total_cards_width) // 2
        start_y = (height - self.CARD_HEIGHT) // 2

        back_img = CardAssetManager.get_image("card_back")
        if back_img:
            for i in range(5):
                x = int(start_x + (self.CARD_WIDTH + self.SPACING) * i)
                y = int(start_y)
                img.paste(back_img, (x, y), back_img)
        return img

    def render_table(self, community_cards: list, pot_amount: int, phase_name: str) -> io.BytesIO:
        """
        コミュニティカードを表示した画像を合成する。
        """
        # ベース画像をコピーして使用
        img = self._base_table.copy()
        width, height = 850, 300

        total_cards_width = (self.CARD_WIDTH * 5) + (self.SPACING * 4)
        start_x = (width - total_cards_width) // 2
        start_y = (height - self.CARD_HEIGHT) // 2

        # 表面のカードのみ上書き
        for i, card in enumerate(community_cards):
            if i >= 5:
                break
            x = int(start_x + (self.CARD_WIDTH + self.SPACING) * i)
            y = int(start_y)

            card_img = self._get_card_image(card)
            if card_img:
                img.paste(card_img, (x, y), card_img)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf

    def render_hand(self, hole_cards: list) -> io.BytesIO:
        """
        手札（ホールカード）2枚を表示した画像を合成する。
        150x220のアセットを 100x145 にリサイズして使用する。
        """
        width = 300
        height = 200
        card_w, card_h = 100, 145
        spacing = 15

        img = Image.new("RGBA", (width, height), self.TABLE_COLOR)

        total_cards_width = (card_w * 2) + spacing
        start_x = (width - total_cards_width) // 2
        start_y = (height - card_h) // 2

        for i in range(2):
            x = int(start_x + (card_w + spacing) * i)
            y = int(start_y)
            if i < len(hole_cards):
                card_img = self._get_card_image(hole_cards[i])
                if card_img:
                    # リサイズして貼り付け
                    resized_card = card_img.resize((card_w, card_h), Image.LANCZOS)
                    img.paste(resized_card, (x, y), resized_card)

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
