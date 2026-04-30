import asyncio
import os
from typing import Dict, Optional

from PIL import Image


class CardAssetManager:
    """
    カードアセットをコンポーネントから動的に合成し、メモリを節約するマネージャー。
    """

    _cache: Dict[str, Image.Image] = {}
    _components: Dict[str, Image.Image] = {}
    _loaded: bool = False
    _load_lock = asyncio.Lock()

    @classmethod
    async def preload(cls):
        """ボット起動時などに非同期でアセットをロードする"""
        async with cls._load_lock:
            if not cls._loaded:
                await asyncio.to_thread(cls._load_all)
        return cls._cache

    @classmethod
    def get_assets(cls) -> Dict[str, Image.Image]:
        """
        互換性のためのメソッド。
        注意: 以前は全カードがロードされていましたが、現在は動的生成されるため
        事前にキャッシュされているもののみを返します。
        確実な取得には `get_image(key)` を使用してください。
        """
        if not cls._loaded:
            cls._load_all()
        return cls._cache

    @classmethod
    def _load_all(cls):
        """全カードアセット（またはコンポーネント）をロードする"""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        assets_dir = os.path.join(base_dir, "data", "card")
        comp_dir = os.path.join(assets_dir, "components")

        if not os.path.exists(comp_dir):
            print(f"Warning: Card components directory not found: {comp_dir}")
            cls._loaded = True
            return

        loaded_count = 0
        # コンポーネントのロード
        for filename in os.listdir(comp_dir):
            if filename.endswith(".png"):
                path = os.path.join(comp_dir, filename)
                try:
                    key = filename.replace(".png", "")
                    cls._components[key] = Image.open(path).convert("RGBA")
                    loaded_count += 1
                except Exception as e:
                    print(f"Warning: Failed to load component {filename}: {e}")

        # 裏面のロード (data/card/card_back.png)
        back_path = os.path.join(assets_dir, "card_back.png")
        if os.path.exists(back_path):
            cls._cache["card_back"] = Image.open(back_path).convert("RGBA")

        # ジョーカーのロード (存在する場合)
        joker_path = os.path.join(assets_dir, "joker.png")
        if os.path.exists(joker_path):
            cls._cache["joker"] = Image.open(joker_path).convert("RGBA")

        # キャッシュの事前生成（スートのベース背景など）
        cls._precompose_bases()

        cls._loaded = True
        print(f"Log: Loaded {loaded_count} card components into memory from {comp_dir}")
        cls._validate_cache()

    @classmethod
    def _precompose_bases(cls):
        """各スートのベースカード（背景＋スートアイコン）を事前合成してキャッシュする"""
        if "base_card" not in cls._components:
            return

        base = cls._components["base_card"]

        for suit in ["S", "H", "D", "C"]:
            suit_key = f"suit_{suit}"
            if suit_key in cls._components:
                # ベースをコピー
                suit_base = base.copy()
                suit_img = cls._components[suit_key]

                # 中央付近にスートを配置
                # ベースが150x220, スートアイコンが元の切り抜き座標によるが、およそ(45, 75)
                suit_base.paste(suit_img, (35, 65), suit_img)

                # コンポーネントとして保存
                cls._components[f"base_{suit}"] = suit_base

    @classmethod
    def _validate_cache(cls):
        if not cls._components:
            print("CRITICAL: No card components were loaded! UI rendering will fail.")
            return

    @classmethod
    def get_image(cls, key: str) -> Optional[Image.Image]:
        """指定されたキーの画像を取得する。未生成なら動的に合成する。"""
        if not cls._loaded:
            cls._load_all()

        # 既にキャッシュ済みならそれを返す
        if key in cls._cache:
            return cls._cache[key]

        # コンポーネントからの動的合成
        # keyの形式: "S_A", "H_10", etc.
        parts = key.split("_")
        if len(parts) != 2:
            return None

        suit, rank = parts[0], parts[1]

        base_key = f"base_{suit}"
        text_key = f"text_{rank}"

        if base_key not in cls._components or text_key not in cls._components:
            return None

        # スートのベースカードをコピー
        card_img = cls._components[base_key].copy()

        # テキスト画像を準備
        text_img = cls._components[text_key].copy()

        # スートに応じた色を設定（抽出したスートアイコンの色に合わせる）
        suit_colors = {
            "C": (44, 160, 44),
            "D": (31, 119, 180),
            "H": (230, 20, 50),
            "S": (15, 15, 15),
        }
        target_color = suit_colors.get(suit, (15, 15, 15))

        pixels = text_img.load()
        for x in range(text_img.width):
            for y in range(text_img.height):
                r, g, b, a = pixels[x, y]
                # 暗いピクセル（黒字）を指定色に変更
                if a > 0 and r < 100 and g < 100 and b < 100:
                    pixels[x, y] = (target_color[0], target_color[1], target_color[2], a)

        # テキストを左上に配置（元の抽出座標: 5, 5）
        card_img.paste(text_img, (10, 5), text_img)

        # 右下にも逆さまにして配置する（オプション）
        rotated_text = text_img.rotate(180)
        # 右下座標（元のサイズ150x220から計算。テキストサイズおよそ35x65）
        # (150 - 5 - 35, 220 - 5 - 65)
        card_img.paste(
            rotated_text, (150 - 10 - text_img.width, 220 - 5 - text_img.height), rotated_text
        )

        # 生成した画像をキャッシュに保存（Lazy caching）
        # これにより2回目以降は爆速になる
        cls._cache[key] = card_img
        return card_img
