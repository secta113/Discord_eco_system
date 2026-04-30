import os
from typing import Dict, Optional

from PIL import ImageFont

from core.utils.logger import Logger


class FontManager:
    """
    フォントアセットをメモリにキャッシュし、描画時のI/O負荷を軽減するマネージャー。
    """

    _cache: Dict[str, ImageFont.FreeTypeFont] = {}
    _loaded: bool = False
    _font_path: Optional[str] = None

    @classmethod
    def preload(cls):
        """フォントをメモリにロードする"""
        if cls._loaded:
            return

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        fonts_dir = os.path.join(base_dir, "data", "fonts")

        # 日本語対応フォントの候補
        font_candidates = [
            os.path.join(fonts_dir, "ja_font_subset.ttf"),
            os.path.join(fonts_dir, "ja_font.ttf"),
            os.path.join(fonts_dir, "ja_font.ttc"),
            "C:\\Windows\\Fonts\\meiryo.ttc",
            "C:\\Windows\\Fonts\\msgothic.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        ]

        for path in font_candidates:
            if os.path.exists(path):
                cls._font_path = path
                break

        if not cls._font_path:
            Logger.warn(
                "FontManager",
                "No suitable Japanese font found. Japanese text may be broken (tofu).",
            )
        else:
            Logger.info("FontManager", f"Font source identified: {cls._font_path}")

        cls._loaded = True

    @classmethod
    def get_font(cls, size: int) -> ImageFont.FreeTypeFont:
        """指定されたサイズのフォントを取得する（キャッシュから優先）"""
        if not cls._loaded:
            cls.preload()

        key = f"font_{size}"
        if key in cls._cache:
            return cls._cache[key]

        try:
            if cls._font_path:
                font = ImageFont.truetype(cls._font_path, size)
                cls._cache[key] = font
                return font
        except Exception as e:
            Logger.error("FontManager", f"Failed to load font at size {size}: {e}")

        # フォールバック
        return ImageFont.load_default()

    @classmethod
    def is_font_available(cls) -> bool:
        """日本語対応フォントが正常に利用可能か（システム標準のフォールバックではないか）を確認する"""
        if not cls._loaded:
            cls.preload()
        # パスが存在し、かつ ImageFont.truetype で読み込み可能であることを（一度だけ）確認済みとする
        return cls._font_path is not None
