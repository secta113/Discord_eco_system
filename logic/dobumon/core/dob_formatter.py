import math
from typing import TYPE_CHECKING, Dict

import discord

if TYPE_CHECKING:
    from logic.dobumon.core.dob_models import Dobumon


class DobumonFormatter:
    """怒武者（ドブモン）の情報を美しく整形するためのフォーマッタークラス。
    ANSIコードブロックやDiscordのEmbedを活用して、ステータスや遺伝情報を可視化します。
    """

    # ANSIカラーコードの定義
    ANSI_RED = "\u001b[1;31m"
    ANSI_YELLOW = "\u001b[1;33m"
    ANSI_BLUE = "\u001b[1;34m"
    ANSI_GREEN = "\u001b[1;32m"
    ANSI_PURPLE = "\u001b[1;35m"
    ANSI_CYAN = "\u001b[1;36m"
    ANSI_RESET = "\u001b[0m"

    @classmethod
    def get_hp_bar(
        cls, current: float, max_val: float, length: int = 10, is_owner: bool = True
    ) -> str:
        """HPゲージの視覚的表現を生成します。

        Args:
            current: 現在のHP/体力
            max_val: 最大HP
            length: バーの文字数
            is_owner: 所有者からの視点かどうか（非所有者には具体的数値を隠す）

        Returns:
            str: [████░░░░] 形式のバー文字列
        """
        ratio = max(0, min(1, current / max_val))
        if ratio > 0:
            filled = max(1, int(math.ceil(ratio * length)))
        else:
            filled = 0
        empty = length - filled
        bar = "█" * filled + "░" * empty

        if not is_owner:
            return f"[{bar}] ??? / ???"
        return f"[{bar}] {int(math.ceil(current))} / {int(math.ceil(max_val))}"

    @classmethod
    def get_iv_hint(cls, iv_val: float) -> str:
        """IV（個体値）に基づいた情緒的な評価ラベルを返します。"""
        if iv_val >= 1.4:
            return f"{cls.ANSI_PURPLE}【伝説的】{cls.ANSI_RESET}"
        if iv_val >= 1.25:
            return f"{cls.ANSI_RED}【驚異的】{cls.ANSI_RESET}"
        if iv_val >= 1.15:
            return f"{cls.ANSI_YELLOW}【素晴らしい】{cls.ANSI_RESET}"
        if iv_val >= 1.05:
            return f"{cls.ANSI_CYAN}【良好】{cls.ANSI_RESET}"
        if iv_val >= 0.95:
            return f"{cls.ANSI_GREEN}【平均的】{cls.ANSI_RESET}"
        if iv_val >= 0.85:
            return f"{cls.ANSI_BLUE}【まずまず】{cls.ANSI_RESET}"
        return f"{cls.ANSI_RESET}【伸び悩み】"

    @classmethod
    def get_stat_grid(cls, dobu: "Dobumon", is_owner: bool = True) -> str:
        """ステータス（攻撃・防御等）を2カラムのANSIグリッド形式で整形します。

        Args:
            dobu: 整形対象のドブモン個体
            is_owner: 所有者からの視点かどうか

        Returns:
            str: ANSIカラーコードを含むテキストブロック
        """
        # 各値の int 化
        hp_max = int(math.ceil(dobu.hp))
        hp_curr = int(math.ceil(dobu.health))

        # HPバー生成
        hp_bar = cls.get_hp_bar(hp_curr, hp_max, length=12, is_owner=is_owner)

        def fmt_val(v: float) -> str:
            return str(int(v)) if is_owner else "???"

        def fmt_hint(stat_key: str) -> str:
            if not is_owner:
                return ""
            # 個体値辞書から取得（デフォルト 1.0）
            iv_val = dobu.iv.get(stat_key, 1.0)
            return f" {cls.get_iv_hint(iv_val)}"

        # グリッド構築（レイアウト保持のためパディングを調整）
        # ANSIコードを含む文字列の長さ調整は難しいため、1列目の後ろに十分なスペースを確保
        def get_line(label1, val1, key1, color1, label2, val2, key2, color2):
            left = f"{color1}{label1}:{cls.ANSI_RESET} {fmt_val(val1)}{fmt_hint(key1)}"
            # 左カラムの幅を概算で調整（全角文字を考慮してスペースを追加）
            # 1.15以上のヒントは長めなので少し広めに取る
            padding = " " * max(1, 22 - (len(fmt_val(val1)) + (12 if is_owner else 0)))
            right = f"{color2}{label2}:{cls.ANSI_RESET} {fmt_val(val2)}{fmt_hint(key2)}"
            return f"{left}{padding}{right}"

        lines = [
            "```ansi",
            f"{cls.ANSI_RED}体力:{cls.ANSI_RESET} {hp_bar}{fmt_hint('hp')}",
            get_line(
                "攻撃",
                dobu.atk,
                "atk",
                cls.ANSI_YELLOW,
                "防御",
                dobu.defense,
                "defense",
                cls.ANSI_BLUE,
            ),
            get_line(
                "回避", dobu.eva, "eva", cls.ANSI_GREEN, "速さ", dobu.spd, "spd", cls.ANSI_PURPLE
            ),
            "```",
        ]
        return "\n".join(lines)

    @classmethod
    def get_vague_gain_text(cls, val: float) -> str:
        """ステータスの変化量を情緒的なテキストで表現します。

        Args:
            val: 変化量（正なら上昇、負なら下降）

        Returns:
            str: プレイヤーに向けた情緒メッセージ
        """
        abs_v = abs(val)
        if val > 0:
            if abs_v <= 0.2:
                return "微かな手応えを感じた"
            if abs_v <= 0.8:
                return "少し成長したようだ"
            if abs_v <= 2.0:
                return "確かな手応えを感じている"
            return "目覚ましい成長を遂げた！"
        elif val < 0:
            if abs_v <= 0.2:
                return "僅かに精彩を欠いた"
            if abs_v <= 0.8:
                return "少し鈍ったようだ"
            return "ガタがきているようだ..."
        return "変化はなかった"

    @classmethod
    def get_bond_text(cls, affection: int) -> str:
        """懐き度に応じたパートナーとの関係性を表現するテキストを生成します。

        Args:
            affection: 懐き度（Affection）の数値

        Returns:
            str: アイコンとメッセージを含むテキスト
        """
        if affection < 0:
            msg, heart = "あなたの視線を避け、どこか悲しげにそっぽを向いています。", "🥀"
        elif affection < 5:
            msg, heart = "呼んでも無視されてしまいます。まだ信頼関係は築けていないようです。", "🍂"
        elif affection < 15:
            msg, heart = "たまにこちらをチラチラと見てくれますが、まだ一定の距離を感じます。", "🌱"
        elif affection < 30:
            msg, heart = "あなたの存在に少しずつ慣れ、信頼が芽生え始めているようです。", "💖"
        elif affection < 50:
            msg, heart = "あなたの手が近づくと、嬉しそうに目を細めるようになりました。", "✨"
        elif affection < 70:
            msg, heart = "あなたを唯一無二のパートナーとして、固い絆で結ばれています。", "🤝"
        elif affection < 100:
            msg, heart = "究極の絆により、言葉を交わさずとも心が通じ合っています。", "🔥"
        else:
            msg, heart = "不滅の愛と信頼を、あなたという存在にすべて捧げています。", "💎"

        return f"{heart} **絆**\n*{msg}*"

    @classmethod
    def get_genetic_info(cls, dobu: "Dobumon", is_owner: bool = True) -> str:
        """世代や発現している遺伝的特性をフォーマットします。

        Args:
            dobu: 整形対象のドブモン個体
            is_owner: 所有者からの視点かどうか

        Returns:
            str: 遺伝情報セクションのテキスト
        """
        gen = getattr(dobu, "generation", 1)
        traits = getattr(dobu, "traits", [])

        lines = [f"🧬 **第 {gen} 世代**"]

        if traits:
            # 特性名のアイコン対応
            trait_icons = {
                "early": "🐣 早熟",
                "late": "🌙 晩成",
                "hardy": "💎 金剛",
                "frail": "🍃 繊細",
                "stable": "⚖️ 安定",
                "burst": "💥 爆発",
                "aesthetic": "✨ 美形",
                "forbidden_red": "🔴 赤の禁忌",
                "forbidden_blue": "🔵 青の禁忌",
                "gold_horn": "👑 金角",
                "red_back": "🎒 赤背",
                "odd_eye": "👁️ 妖眼",
                "blue_blood": "💉 青血",
                "anti_taboo": "🏹 対禁忌",
                "antinomy": "🔗 背反",
                "the_forbidden": "🌠 禁断",
                "unlimited": "♾️ 無限",
                "parasitic": "🕸️ 捕食",
                "undead": "💀 不死",
                "crystalized": "💎 結晶化",
                "chimera": "🧬 合成獣",
                "glass_blade": "⚔️ 硝子の刃",
                "supernova": "🌟 超新星",
                "singularity": "⚫ 特異点",
            }
            display_traits = [trait_icons.get(t, f"✨ {t}") for t in traits]
            lines.append(f"固有特性: {', '.join(display_traits)}")

        if is_owner:
            inbreeding = dobu.genetics.get("inbreeding_debt", 0)
            if inbreeding > 0:
                lines.append(f"⚠️ **親等係数 (COI)**: {inbreeding * 100:.2f}%")

        return "\n".join(lines)

    @classmethod
    def format_status_embed(cls, dobu: "Dobumon", is_owner: bool = True) -> discord.Embed:
        """ステータス画面表示用の Discord Embed を構築します。

        Args:
            dobu: 表示対象のドブモン個体
            is_owner: コマンド実行者が所有者かどうか

        Returns:
            discord.Embed: 整形済みの Embed オブジェクト
        """
        # 属性に応じた Embed カラー
        attr_colors = {
            "fire": 0xE74C3C,  # 赤
            "water": 0x3498DB,  # 青
            "grass": 0x2ECC71,  # 緑
        }
        color = attr_colors.get(dobu.attribute, 0x95A5A6)

        embed = discord.Embed(title=f"👹 {dobu.name}", color=color)

        gender_icon = "♂️" if dobu.gender == "M" else "♀️"

        # ライフステージに応じた二つ名
        stage_names = {
            "young": "🐣 幼年期",
            "prime": "🔥 全盛期",
            "senior": "🌙 熟練期",
            "twilight": "🕯️ 晩年期",
        }
        stage_name = stage_names.get(dobu.life_stage, "不明")

        status_line = (
            f"性別: {gender_icon} | 属性: {dobu.attribute.upper()} | ステージ: {stage_name}"
        )
        if is_owner:
            ratio_int = (
                int((dobu.lifespan / dobu.max_lifespan) * 100) if dobu.max_lifespan > 0 else 0
            )
            status_line += f" ({ratio_int}% 残り)"

        if not dobu.is_alive:
            status_line += " | 状態: 🪦 死亡"
        elif dobu.is_sterile:
            status_line += " | 状態: ⚔️ 戦闘特化(生殖不可)"
        else:
            status_line += " | 状態: 生存"

        # 寿命（バイタル）バーの構築
        # 初期寿命（max_lifespan）を分母としてバーを表示
        vitality_bar = cls.get_hp_bar(
            int(dobu.lifespan), dobu.max_lifespan, length=12, is_owner=is_owner
        )
        vitality_line = f"🧬 **バイタル**: {vitality_bar}"
        if is_owner:
            if dobu.life_stage == "twilight":
                vitality_line += (
                    f"\n{cls.ANSI_RED}⚠️ 生命が今にも消えかかっています...{cls.ANSI_RESET}"
                )

        grid = cls.get_stat_grid(dobu, is_owner=is_owner)
        genetics = cls.get_genetic_info(dobu, is_owner=is_owner)

        if is_owner:
            bond = cls.get_bond_text(getattr(dobu, "affection", 0))
        else:
            bond = "💖 **絆**\n*その怒武者が誰を信じているのか、あなたには分かりません。*"

        # 表示情報を統合
        lines = [
            status_line,
            vitality_line,
            "━━━━━━ Genetics ━━━━━━",
            genetics,
            "━━━━━━ Status ━━━━━━",
            grid,
            bond,
        ]

        if dobu.win_count > 0:
            val = dobu.win_count if is_owner else "???"
            lines.append(f"\n† **勝利数**: {val}")

        embed.description = "\n".join(lines)
        return embed

    @classmethod
    def format_training_result_embed(
        cls, dobu: "Dobumon", menu: str, result: Dict
    ) -> discord.Embed:
        """トレーニング結果の埋め込みメッセージを作成する"""
        gains = result["gains"]
        is_great = result.get("is_great", False)
        overworked = result["overworked"]
        lifespan_lost = result["lifespan_lost"]
        is_alive = result["is_alive"]

        menu_name = {
            "strength": "筋トレ",
            "running": "走り込み",
            "ukemi": "受け身",
            "shadow": "シャドーボクシング",
            "sparring": "スパーリング",
            "massage": "マッサージ・お昼寝",
        }.get(menu, menu)

        title = f"🏋️ {menu_name}完了！"
        color = 0x3498DB
        if is_great:
            title = f"✨ 大成功！！ {menu_name}完了！"
            color = 0xF1C40F

        embed = discord.Embed(title=title, color=color)

        # ステータス変化
        stat_labels = {
            "hp": "HP",
            "atk": "攻撃力",
            "defense": "防御力",
            "eva": "回避力",
            "spd": "行動力",
        }
        gain_texts = [
            f"{stat_labels.get(s, s.upper())} **{cls.get_vague_gain_text(v)}**"
            for s, v in gains.items()
            if v != 0
        ]
        msg = (
            "基礎能力が変化しました：\n" + (", ".join(gain_texts))
            if gain_texts
            else "ステータスに変化はありませんでした。"
        )

        # 体力変化
        if result["fatigue_rate"] > 0:
            msg += "\n\n🩺 トレーニングにより体力を消耗しました。"
        elif result["fatigue_rate"] < 0:
            msg += "\n\n💤 心身ともにリフレッシュしました！"

        # オーバーワーク
        if overworked:
            if result.get("safe"):
                msg += "\n\n🧘 今日はもう無理はやめよう。休息は明日への活力だ。"
            else:
                msg += "\n\n⚠️ **オーバーワーク状態です！** 寿命が削れるリスクがあります。"
                if lifespan_lost:
                    msg += "\n💀 無理が祟り、寿命が **-1** 減少しました..."

        if is_alive and result.get("learned_skill"):
            msg += f"\n\n✨ **新技習得！** **{dobu.name}** が「{result['learned_skill']}」の極意を掴みました！"

        if not is_alive:
            embed.title, embed.color = f"🪦 {dobu.name} が力尽きました...", 0x7F8C8D
            msg += f"\n\n過酷な連戦に耐えきれず、**{dobu.name}** は息を引き取った..."

        embed.description = msg
        return embed

    @classmethod
    def format_error_embed(cls, message: str) -> discord.Embed:
        """ドブモン専用のエラーEmbedを構築します。"""
        embed = discord.Embed(
            title="⚠️ エラー",
            description=message,
            color=0xCC0000,  # 濃い赤
        )
        embed.set_footer(text="Discord Economy System - Dobumon Engine")
        return embed
