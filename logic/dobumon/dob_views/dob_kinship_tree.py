import io
from typing import Any, Dict, List, Optional, Set, Tuple

from PIL import Image, ImageDraw

from core.utils.font_manager import FontManager
from core.utils.logger import Logger
from logic.dobumon.core.dob_models import Dobumon


class DobumonKinshipTree:
    """
    怒武者（ドブモン）のビジュアル家系図（親等図）を生成するクラス。
    ダークテーマとグラスモーフィズムデザインを採用し、親子関係を視覚的に表示します。
    """

    # カラー定義
    BG_COLOR = (15, 15, 20, 255)
    CARD_BG = (40, 40, 50, 200)
    BORDER_COLOR = (80, 80, 100, 255)
    TEXT_COLOR = (240, 240, 240)
    GHOST_COLOR = (100, 100, 100)
    CONNECTOR_COLOR = (120, 120, 150, 180)

    ATTR_COLORS = {
        "fire": (231, 76, 60),
        "water": (52, 152, 219),
        "grass": (46, 204, 113),
    }

    # 制限値
    MAX_NODES = 100  # 描画する最大ノード数（メモリ保護）
    MAX_DEPTH = 10  # 遡る最大世代数（5親等＋α）

    def __init__(self):
        # FontManagerを使用してフォントを取得
        self.font_main = FontManager.get_font(20)
        self.font_small = FontManager.get_font(14)
        self.font_title = FontManager.get_font(32)

    def render_pedigree_map(
        self,
        user_name: str,
        current_dobumons: List[Dobumon],
        owner_id: int,
        repo: Optional[Any] = None,
        target_ids: Optional[List[str]] = None,
    ) -> io.BytesIO:
        """
        所持ドブモンの家系図マップをレンダリングします。
        """
        # フォントの利用可能性を検証
        if not FontManager.is_font_available():
            Logger.warn("Dobumon", "Font rendering may be broken due to missing Japanese font.")

        # 1. グラフの構築
        id_to_dobu, child_to_parents, all_ids = self._build_graph(current_dobumons, owner_id, repo)

        # もし target_ids が指定されていれば、関連するノードのみにフィルタリング
        if target_ids:
            all_ids, child_to_parents = self._filter_graph_by_target(
                target_ids, all_ids, child_to_parents
            )

        # ノード数が多すぎる場合は、描画対象をさらに制限（安全策）
        if len(all_ids) > self.MAX_NODES:
            Logger.warn("Dobumon", f"Too many nodes in map ({len(all_ids)}). Limiting display.")
            all_ids = set(list(all_ids)[: self.MAX_NODES])

        # 2. 階層（世代）の決定
        generations: Dict[int, List[str]] = {}
        for uid in all_ids:
            dobu = id_to_dobu.get(uid)
            gen = dobu.generation if dobu else self._guess_generation(uid, current_dobumons)
            if gen not in generations:
                generations[gen] = []
            generations[gen].append(uid)

        sorted_gens = sorted(generations.keys())
        if not sorted_gens:
            return self._render_empty_map(user_name)

        # 3. ダイナミックなキャンバスサイズの計算
        card_w, card_h = 240, 110
        padding = 60
        max_nodes_per_gen = max(len(uids) for uids in generations.values())
        gen_spacing_val = 150

        width = min(4000, max(1400, len(sorted_gens) * (card_w + gen_spacing_val) + padding * 2))
        height = min(4000, max(800, max_nodes_per_gen * (card_h + padding) + padding * 2 + 100))

        try:
            img = Image.new("RGBA", (width, height), self.BG_COLOR)
        except MemoryError:
            Logger.error("Dobumon", f"MemoryError creating image canvas ({width}x{height})")
            return self._render_error_map("Memory Error (Map too large)")

        draw = ImageDraw.Draw(img)

        # 4. ノード座標の計算
        node_coords = self._calculate_node_coords(
            sorted_gens, generations, child_to_parents, width, padding, card_w, card_h, height
        )

        # 5. コネクタ（親子関係の線）の描画
        for child_id, parents in child_to_parents.items():
            if child_id not in node_coords:
                continue
            cx, cy = node_coords[child_id]
            for p_idx, p_id in enumerate(parents):
                if p_id in node_coords:
                    px, py = node_coords[p_id]
                    start_pos = (px + card_w, py + card_h // 2)
                    end_pos = (cx, cy + card_h // 2)
                    self._draw_connector(draw, start_pos, end_pos, p_idx)

        # 5. ノード（カード）の描画
        for uid, coords in node_coords.items():
            dobu = id_to_dobu.get(uid)
            self._draw_node(draw, coords[0], coords[1], card_w, card_h, dobu)

        # タイトル
        draw.text(
            (padding, 20),
            f"〓 {user_name} 怒武者血統地図 〓",
            font=self.font_title,
            fill=(255, 215, 0),
        )

        # 出力
        img_output = img.convert("RGB")
        buf = io.BytesIO()
        img_output.save(buf, format="PNG")
        buf.seek(0)
        return buf

    def _extract_parents(self, lineage: List[str]) -> List[str]:
        parents = []
        for entry in lineage:
            if "|" in entry:
                parts = entry.split("|")
                if len(parts) >= 2 and parts[1] == "1":
                    parents.append(parts[0])
            else:
                parents.append(entry)
        return parents

    def _build_graph(
        self, current_dobumons: List[Dobumon], owner_id: int, repo: Optional[Any]
    ) -> Tuple[Dict[str, Optional[Dobumon]], Dict[str, List[str]], Set[str]]:
        id_to_dobu: Dict[str, Optional[Dobumon]] = {d.dobumon_id: d for d in current_dobumons}
        child_to_parents: Dict[str, List[str]] = {}
        all_ids = set(id_to_dobu.keys())

        id_to_depth: Dict[str, int] = {d.dobumon_id: 0 for d in current_dobumons}
        queue = list(all_ids)
        processed_ids = set()

        while queue:
            current_id = queue.pop(0)
            if current_id in processed_ids:
                continue
            processed_ids.add(current_id)

            depth = id_to_depth.get(current_id, 0)
            if depth >= self.MAX_DEPTH:
                continue

            dobu = id_to_dobu.get(current_id)
            if not dobu and repo:
                schema = repo.get_dobumon(current_id)
                if schema:
                    data = (
                        schema.model_dump() if hasattr(schema, "model_dump") else schema.to_dict()
                    )
                    dobu = Dobumon(**data)
                    id_to_dobu[current_id] = dobu
                    all_ids.add(current_id)

            if dobu:
                is_current_owner = dobu.owner_id == owner_id
                parents = self._extract_parents(dobu.lineage)
                child_to_parents[current_id] = parents

                # 探索の継続条件:
                # 1. 5親等までは所有者に関わらず遡る（近親判定に必要）
                # 2. 5親等以降は、自分が所有している個体であれば遡る
                should_continue = (depth < 5) or is_current_owner

                if should_continue:
                    for p_id in parents:
                        if p_id not in id_to_dobu:
                            id_to_dobu[p_id] = None
                        if p_id not in processed_ids:
                            id_to_depth[p_id] = depth + 1
                            queue.append(p_id)
                        all_ids.add(p_id)
                else:
                    # 探索は止めるが、親の存在だけは記録して線が引けるようにする
                    for p_id in parents:
                        all_ids.add(p_id)
                        if p_id not in id_to_dobu:
                            id_to_dobu[p_id] = None

            if len(all_ids) > 500:
                Logger.warn("Dobumon", "Kinship graph search aborted: Too many nodes found.")
                break

        return id_to_dobu, child_to_parents, all_ids

    def _filter_graph_by_target(
        self, target_ids: List[str], all_ids: Set[str], child_to_parents: Dict[str, List[str]]
    ) -> Tuple[Set[str], Dict[str, List[str]]]:
        valid_targets = [tid for tid in target_ids if tid in all_ids]
        if not valid_targets:
            return all_ids, child_to_parents

        keep_ids = set(valid_targets)
        ancestor_queue = list(valid_targets)
        while ancestor_queue:
            curr = ancestor_queue.pop(0)
            for p in child_to_parents.get(curr, []):
                if p not in keep_ids:
                    keep_ids.add(p)
                    ancestor_queue.append(p)

        parent_to_children: Dict[str, List[str]] = {}
        for c_id, p_ids in child_to_parents.items():
            for p_id in p_ids:
                if p_id not in parent_to_children:
                    parent_to_children[p_id] = []
                parent_to_children[p_id].append(c_id)

        descendant_queue = list(valid_targets)
        while descendant_queue:
            curr = descendant_queue.pop(0)
            for c in parent_to_children.get(curr, []):
                if c not in keep_ids:
                    keep_ids.add(c)
                    descendant_queue.append(c)

        filtered_ids = all_ids.intersection(keep_ids)
        filtered_parents = {
            k: [p for p in v if p in filtered_ids]
            for k, v in child_to_parents.items()
            if k in filtered_ids
        }
        return filtered_ids, filtered_parents

    def _calculate_node_coords(
        self,
        sorted_gens: List[int],
        generations: Dict[int, List[str]],
        child_to_parents: Dict[str, List[str]],
        width: int,
        padding: int,
        card_w: int,
        card_h: int,
        height: int,
    ) -> Dict[str, Tuple[int, int]]:
        node_coords: Dict[str, Tuple[int, int]] = {}
        gen_column_width = (
            (width - padding * 2 - card_w) // max(1, (len(sorted_gens) - 1))
            if len(sorted_gens) > 1
            else 0
        )

        for g_idx, gen in enumerate(sorted_gens):
            uids = generations[gen]
            x = padding + g_idx * gen_column_width

            if g_idx > 0:

                def get_avg_parent_y(uid):
                    parents = child_to_parents.get(uid, [])
                    y_sum = 0
                    count = 0
                    for p in parents:
                        if p in node_coords:
                            y_sum += node_coords[p][1]
                            count += 1
                    return y_sum / count if count > 0 else float("inf")

                uids.sort(key=get_avg_parent_y)

            total_h = len(uids) * (card_h + padding)
            start_y = (height - total_h) // 2 + 40
            for i, uid in enumerate(uids):
                y = start_y + i * (card_h + padding)
                node_coords[uid] = (x, y)

        return node_coords

    def _guess_generation(self, parent_id: str, current_dobumons: List[Dobumon]) -> int:
        for dobu in current_dobumons:
            if parent_id in self._extract_parents(dobu.lineage):
                return max(1, dobu.generation - 1)
        return 1

    def _draw_connector(
        self, draw: ImageDraw, start: Tuple[int, int], end: Tuple[int, int], p_idx: int
    ):
        offset_y = (p_idx - 0.5) * 40 if p_idx < 2 else 0
        adj_end = (end[0], end[1] + offset_y)
        dist_x = adj_end[0] - start[0]
        p1 = (start[0] + dist_x * 0.4, start[1])
        p2 = (adj_end[0] - dist_x * 0.4, adj_end[1])
        curve_points = []
        steps = 20
        for i in range(steps + 1):
            t = i / steps
            ox = (
                (1 - t) ** 3 * start[0]
                + 3 * (1 - t) ** 2 * t * p1[0]
                + 3 * (1 - t) * t**2 * p2[0]
                + t**3 * adj_end[0]
            )
            oy = (
                (1 - t) ** 3 * start[1]
                + 3 * (1 - t) ** 2 * t * p1[1]
                + 3 * (1 - t) * t**2 * p2[1]
                + t**3 * adj_end[1]
            )
            curve_points.append((ox, oy))
        draw.line(curve_points, fill=self.CONNECTOR_COLOR, width=3)
        draw.polygon(
            [adj_end, (adj_end[0] - 12, adj_end[1] - 6), (adj_end[0] - 12, adj_end[1] + 6)],
            fill=self.CONNECTOR_COLOR,
        )

    def _draw_node(self, draw: ImageDraw, x, y, w, h, dobu: Optional[Dobumon]):
        if dobu:
            bg = self.CARD_BG
            if not dobu.is_alive:
                bg = (30, 30, 35, 200)

            draw.rectangle([x, y, x + w, y + h], fill=bg, outline=self.BORDER_COLOR, width=1)
            attr_c = self.ATTR_COLORS.get(dobu.attribute, (128, 128, 128))
            draw.ellipse([x + 10, y + 10, x + 25, y + 25], fill=attr_c)
            text_color = self.TEXT_COLOR if dobu.is_alive else self.GHOST_COLOR
            name_text = dobu.name
            draw.text((x + 35, y + 8), name_text, font=self.font_main, fill=text_color)
            if not dobu.is_alive:
                if getattr(dobu, "is_sold", False):
                    draw.text(
                        (x + w - 60, y + 42),
                        "（売却）",
                        font=self.font_small,
                        fill=self.GHOST_COLOR,
                    )
                else:
                    self._draw_tombstone_icon(draw, x + w - 55, y + 40)
            gender_icon = "♂" if dobu.gender == "M" else "♀"
            gender_color = (135, 206, 250) if dobu.gender == "M" else (255, 182, 193)
            draw.text((x + w - 25, y + 8), gender_icon, font=self.font_main, fill=gender_color)
            details = f"Gen {dobu.generation} | {self._translate_stage(dobu.life_stage)}"
            draw.text((x + 10, y + 40), details, font=self.font_small, fill=text_color)
            if dobu.is_alive:
                bar_y = y + h - 15
                ratio = dobu.lifespan / dobu.max_lifespan if dobu.max_lifespan > 0 else 0
                draw.rectangle([x + 10, bar_y, x + w - 10, bar_y + 4], fill=(60, 60, 60))
                draw.rectangle(
                    [x + 10, bar_y, x + 10 + int((w - 20) * ratio), bar_y + 4], fill=(46, 204, 113)
                )
        else:
            draw.rectangle(
                [x, y, x + w, y + h], fill=(20, 20, 25, 150), outline=(50, 50, 60), width=1
            )
            draw.text(
                (x + (w - 60) // 2, y + (h - 20) // 2),
                "？？？",
                font=self.font_main,
                fill=self.GHOST_COLOR,
            )

    def _draw_tombstone_icon(self, draw: ImageDraw, x, y):
        w, h = 20, 25
        draw.rectangle([x, y + 5, x + w, y + h], fill=(120, 120, 130), outline=(80, 80, 90))
        draw.ellipse([x, y, x + w, y + 10], fill=(120, 120, 130), outline=(80, 80, 90))
        draw.line([x + 10, y + 8, x + 10, y + 18], fill=(60, 60, 70), width=2)
        draw.line([x + 6, y + 12, x + 14, y + 12], fill=(60, 60, 70), width=2)

    def _translate_stage(self, stage: str) -> str:
        mapping = {"young": "幼年", "prime": "全盛", "senior": "熟練", "twilight": "晩年"}
        return mapping.get(stage, "不明")

    def _render_empty_map(self, user_name: str) -> io.BytesIO:
        img = Image.new("RGB", (800, 400), (15, 15, 20))
        draw = ImageDraw.Draw(img)
        draw.text(
            (250, 180), "所持している怒武者がいません", font=self.font_main, fill=(150, 150, 150)
        )
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf

    def _render_error_map(self, error_msg: str) -> io.BytesIO:
        img = Image.new("RGB", (800, 400), (40, 20, 20))
        draw = ImageDraw.Draw(img)
        draw.text((200, 180), f"Error: {error_msg}", font=self.font_main, fill=(255, 100, 100))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf
