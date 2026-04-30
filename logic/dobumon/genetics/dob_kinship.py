from typing import Dict, List, Optional, Tuple


class KinshipLogic:
    """
    家系図の解析、親等の算出、近親係数(COI)の計算を一元管理するクラス。
    """

    @staticmethod
    def parse_lineage(lineage: List[str]) -> Dict[str, Tuple[int, float]]:
        """
        家系図リストを { id: (depth, f_value) } の辞書に変換します。
        """
        parsed = {}
        for entry in lineage:
            parts = entry.split("|")
            if len(parts) == 3:
                uid, depth, f_val = parts[0], int(parts[1]), float(parts[2])
                parsed[uid] = (depth, f_val)
            else:
                # 旧形式
                parsed[entry] = (5, 0.0)
        return parsed

    @staticmethod
    def calculate_coi(
        p1_id: str,
        p1_parsed: Dict[str, Tuple[int, float]],
        p2_id: str,
        p2_parsed: Dict[str, Tuple[int, float]],
    ) -> float:
        """
        Wrightの近親係数 (COI) を計算します。
        F = sum( (1/2)^(n1 + n2 + 1) * (1 + f_A) )
        """
        f = 0.0
        # 1. 共通の先祖を探す
        common_ids = set(p1_parsed.keys()) & set(p2_parsed.keys())
        for aid in common_ids:
            d1, f1 = p1_parsed[aid]
            d2, f2 = p2_parsed[aid]
            # 6親等以上は無視
            if d1 + d2 >= 6:
                continue
            f += (0.5 ** (d1 + d2 + 1)) * (1.0 + f1)

        # 2. 片方の親がもう片方の親の先祖である場合 (親子交配など)
        if p1_id in p2_parsed:
            d2, f1 = p2_parsed[p1_id]
            if d2 < 6:
                f += (0.5 ** (0 + d2 + 1)) * (1.0 + f1)
        if p2_id in p1_parsed:
            d1, f2 = p1_parsed[p2_id]
            if d1 < 6:
                f += (0.5 ** (d1 + 0 + 1)) * (1.0 + f2)

        return round(min(0.99, f), 4)

    @staticmethod
    def get_kinship_degree(
        p1_id: str,
        p1_parsed: Dict[str, Tuple[int, float]],
        p2_id: str,
        p2_parsed: Dict[str, Tuple[int, float]],
    ) -> Optional[int]:
        """
        2体間の親等 (Degree of Kinship) を計算します。
        共通先祖までの最短パスの合計を返します。
        """
        degrees = []

        # 1. 同一名称（同一ID）チェック
        if p1_id == p2_id:
            return 0

        # 2. 共通先祖の探索
        common_ids = set(p1_parsed.keys()) & set(p2_parsed.keys())
        for aid in common_ids:
            d1, _ = p1_parsed[aid]
            d2, _ = p2_parsed[aid]
            degrees.append(d1 + d2)

        # 3. 直接の血縁（親子など）の探索
        if p1_id in p2_parsed:
            d2, _ = p2_parsed[p1_id]
            degrees.append(d2)
        if p2_id in p1_parsed:
            d1, _ = p1_parsed[p2_id]
            degrees.append(d1)

        return min(degrees) if degrees else None

    @staticmethod
    def update_lineage_list(
        p1_id: str,
        p1_f: float,
        p1_parsed: Dict[str, Tuple[int, float]],
        p2_id: str,
        p2_f: float,
        p2_parsed: Dict[str, Tuple[int, float]],
        max_depth: int = 5,
    ) -> List[str]:
        """
        子の新しい家系図リストを作成します。
        """
        new_parsed = {}
        new_parsed[p1_id] = (1, p1_f)
        new_parsed[p2_id] = (1, p2_f)

        for parent_parsed in [p1_parsed, p2_parsed]:
            for aid, (depth, f_val) in parent_parsed.items():
                new_depth = depth + 1
                if new_depth <= max_depth:
                    if aid not in new_parsed or new_depth < new_parsed[aid][0]:
                        new_parsed[aid] = (new_depth, f_val)

        return [f"{uid}|{d}|{f}" for uid, (d, f) in new_parsed.items()]

    @staticmethod
    def calculate_inbreeding_penalties(inbreeding_f: float) -> Dict[str, float]:
        """
        COIに基づき、寿命の減少率と病気率の上昇値を計算します。
        """
        # 1. 寿命減少率 (乗算)
        # F=0.25 で 約84% に減少 (0.5^0.25)
        lifespan_penalty_rate = (1.0 - (0.5**inbreeding_f)) if inbreeding_f > 0 else 0.0

        # 2. 病気率上昇 (加算)
        # F=0.25 で 10% 上昇 (inbreeding_f * 0.4)
        illness_gain = inbreeding_f * 0.4

        return {
            "lifespan_penalty_pct": round(lifespan_penalty_rate * 100, 1),
            "illness_gain_pct": round(illness_gain * 100, 1),
        }
