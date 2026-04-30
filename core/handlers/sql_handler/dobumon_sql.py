import datetime
import json
from typing import Any, Dict, List, Optional

from .db_base import _get_connection


def upsert_dobumon(db_path: str, domu_data: Dict[str, Any]) -> None:
    """怒武者のデータを保存・更新します。存在しない場合は新規作成、存在する場合は更新(UPSERT)します。

    Args:
        db_path: データベースのパス
        domu_data: 保存するドブモンのデータ辞書（Dobumon.to_dict() 形式）
    """
    jst_now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    updated_at = jst_now.isoformat()
    if "created_at" not in domu_data or not domu_data["created_at"]:
        domu_data["created_at"] = updated_at

    skills_json = json.dumps(domu_data.get("skills", []), ensure_ascii=False)
    iv_json = json.dumps(domu_data.get("iv", {}), ensure_ascii=False)
    genetics_json = json.dumps(domu_data.get("genetics", {}), ensure_ascii=False)
    lineage_json = json.dumps(domu_data.get("lineage", []), ensure_ascii=False)
    traits_json = json.dumps(domu_data.get("traits", []), ensure_ascii=False)
    shop_flags_json = json.dumps(domu_data.get("shop_flags", {}), ensure_ascii=False)

    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO dobumons (
                dobumon_id, owner_id, name, gender, hp, atk, defense, eva, spd,
                health, skills, iv, lifespan, is_alive, attribute, affection,
                genetics, lineage, traits, win_count, rank, generation, last_train_date, today_train_count,
                is_sterile, can_extend_lifespan, illness_rate, today_affection_gain, today_wild_battle_count, today_massage_count,
                max_lifespan, shop_flags, is_sold, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(dobumon_id) DO UPDATE SET
                owner_id = excluded.owner_id,
                name = excluded.name,
                gender = excluded.gender,
                hp = excluded.hp,
                atk = excluded.atk,
                defense = excluded.defense,
                eva = excluded.eva,
                spd = excluded.spd,
                health = excluded.health,
                skills = excluded.skills,
                iv = excluded.iv,
                lifespan = excluded.lifespan,
                is_alive = excluded.is_alive,
                attribute = excluded.attribute,
                affection = excluded.affection,
                genetics = excluded.genetics,
                lineage = excluded.lineage,
                traits = excluded.traits,
                win_count = excluded.win_count,
                rank = excluded.rank,
                generation = excluded.generation,
                last_train_date = excluded.last_train_date,
                today_train_count = excluded.today_train_count,
                is_sterile = excluded.is_sterile,
                can_extend_lifespan = excluded.can_extend_lifespan,
                illness_rate = excluded.illness_rate,
                today_affection_gain = excluded.today_affection_gain,
                today_wild_battle_count = excluded.today_wild_battle_count,
                today_massage_count = excluded.today_massage_count,
                max_lifespan = excluded.max_lifespan,
                shop_flags = excluded.shop_flags,
                is_sold = excluded.is_sold,
                updated_at = excluded.updated_at
        """,
            (
                domu_data["dobumon_id"],
                str(domu_data["owner_id"]),
                domu_data["name"],
                domu_data["gender"],
                domu_data["hp"],
                domu_data["atk"],
                domu_data["defense"],
                domu_data["eva"],
                domu_data["spd"],
                domu_data.get("health", domu_data["hp"]),
                skills_json,
                iv_json,
                domu_data.get("lifespan", 100),
                1 if domu_data.get("is_alive", True) else 0,
                domu_data.get("attribute", ""),
                domu_data.get("affection", 0),
                genetics_json,
                lineage_json,
                traits_json,
                domu_data.get("win_count", 0),
                domu_data.get("rank", 0),
                domu_data.get("generation", 1),
                domu_data.get("last_train_date", "1970-01-01"),
                domu_data.get("today_train_count", 0),
                1 if domu_data.get("is_sterile", False) else 0,
                1 if domu_data.get("can_extend_lifespan", True) else 0,
                domu_data.get("illness_rate", 0.01),
                domu_data.get("today_affection_gain", 0),
                domu_data.get("today_wild_battle_count", 0),
                domu_data.get("today_massage_count", 0),
                domu_data.get("max_lifespan", 100),
                shop_flags_json,
                1 if domu_data.get("is_sold", False) else 0,
                domu_data["created_at"],
                updated_at,
            ),
        )
        conn.commit()


def get_dobumon(db_path: str, dobumon_id: str) -> Optional[Dict[str, Any]]:
    """指定したドブモンIDのデータを取得します。

    Args:
        db_path: データベースのパス
        dobumon_id: 取得対象のドブモンID

    Returns:
        Optional[Dict[str, Any]]: 格納されたデータの辞書。存在しない場合は None。
    """
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dobumons WHERE dobumon_id = ?", (dobumon_id,))
        row = cursor.fetchone()
        if row:
            data = dict(row)
            # JSON形式のフィールドをデコード
            data["skills"] = json.loads(data["skills"]) if data["skills"] else []
            data["iv"] = json.loads(data["iv"]) if data["iv"] else {}
            data["genetics"] = json.loads(data["genetics"]) if data["genetics"] else {}
            data["lineage"] = json.loads(data["lineage"]) if data.get("lineage") else []
            data["traits"] = json.loads(data["traits"]) if data.get("traits") else []
            data["shop_flags"] = json.loads(data["shop_flags"]) if data.get("shop_flags") else {}
            # 真偽値・数値の変換
            data["is_alive"] = bool(data["is_alive"])
            data["is_sold"] = bool(data.get("is_sold", 0))
            data["is_sterile"] = bool(data.get("is_sterile", 0))
            data["can_extend_lifespan"] = bool(data.get("can_extend_lifespan", 1))
            return data
        return None


def get_user_dobumons(db_path: str, owner_id: int, only_alive: bool = True) -> List[Dict[str, Any]]:
    """指定したユーザーが所有するドブモンの一覧を取得します。

    Args:
        db_path: データベースのパス
        owner_id: 所有者のユーザーID
        only_alive: 生存している個体のみ取得するかどうか

    Returns:
        List[Dict[str, Any]]: 取得されたドブモンデータのリスト
    """
    query = "SELECT * FROM dobumons WHERE owner_id = ?"
    if only_alive:
        query += " AND is_alive = 1"

    # 売却済み個体は所持リストに含めない
    query += " AND is_sold = 0"

    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, (str(owner_id),))
        results = []
        for row in cursor.fetchall():
            data = dict(row)
            data["skills"] = json.loads(data["skills"]) if data["skills"] else []
            data["iv"] = json.loads(data["iv"]) if data["iv"] else {}
            data["genetics"] = json.loads(data["genetics"]) if data["genetics"] else {}
            data["lineage"] = json.loads(data["lineage"]) if data.get("lineage") else []
            data["traits"] = json.loads(data["traits"]) if data.get("traits") else []
            data["shop_flags"] = json.loads(data["shop_flags"]) if data.get("shop_flags") else {}
            data["is_alive"] = bool(data["is_alive"])
            data["is_sold"] = bool(data.get("is_sold", 0))
            data["is_sterile"] = bool(data.get("is_sterile", 0))
            data["can_extend_lifespan"] = bool(data.get("can_extend_lifespan", 1))
            results.append(data)
        return results


def get_dobumons_by_name(db_path: str, name: str) -> List[Dict[str, Any]]:
    """名前（完全一致）を指定して、全所有者からドブモンを取得します。

    Args:
        db_path: データベースのパス
        name: 検索するドブモンの名前

    Returns:
        List[Dict[str, Any]]: 該当するドブモンデータのリスト
    """
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dobumons WHERE name = ?", (name,))
        results = []
        for row in cursor.fetchall():
            data = dict(row)
            data["skills"] = json.loads(data["skills"]) if data["skills"] else []
            data["iv"] = json.loads(data["iv"]) if data["iv"] else {}
            data["genetics"] = json.loads(data["genetics"]) if data["genetics"] else {}
            data["lineage"] = json.loads(data["lineage"]) if data.get("lineage") else []
            data["traits"] = json.loads(data["traits"]) if data.get("traits") else []
            data["shop_flags"] = json.loads(data["shop_flags"]) if data.get("shop_flags") else {}
            data["is_alive"] = bool(data["is_alive"])
            data["is_sold"] = bool(data.get("is_sold", 0))
            data["is_sterile"] = bool(data.get("is_sterile", 0))
            data["can_extend_lifespan"] = bool(data.get("can_extend_lifespan", 1))
            results.append(data)
        return results


def get_all_alive_dobumons(db_path: str) -> List[Dict[str, Any]]:
    """全所有者の生存しているドブモンをすべて取得します（自然加齢処理用）。

    Args:
        db_path: データベースのパス

    Returns:
        List[Dict[str, Any]]: 取得されたドブモンデータのリスト
    """
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dobumons WHERE is_alive = 1")
        results = []
        for row in cursor.fetchall():
            data = dict(row)
            data["skills"] = json.loads(data["skills"]) if data["skills"] else []
            data["iv"] = json.loads(data["iv"]) if data["iv"] else {}
            data["genetics"] = json.loads(data["genetics"]) if data["genetics"] else {}
            data["lineage"] = json.loads(data["lineage"]) if data.get("lineage") else []
            data["traits"] = json.loads(data["traits"]) if data.get("traits") else []
            data["shop_flags"] = json.loads(data["shop_flags"]) if data.get("shop_flags") else {}
            data["is_alive"] = bool(data["is_alive"])
            data["is_sold"] = bool(data.get("is_sold", 0))
            data["is_sterile"] = bool(data.get("is_sterile", 0))
            data["can_extend_lifespan"] = bool(data.get("can_extend_lifespan", 1))
            results.append(data)
        return results


def delete_dobumon(db_path: str, dobumon_id: str) -> None:
    """指定したドブモンをデータベースから削除します。
    売却時などに使用します。

    Args:
        db_path: データベースのパス
        dobumon_id: 削除対象のドブモンID
    """
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM dobumons WHERE dobumon_id = ?", (dobumon_id,))
        conn.commit()
