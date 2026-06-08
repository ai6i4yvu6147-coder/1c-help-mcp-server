"""Import help from unpacked HBK (shcntx_ru, shlang_ru, shquery_ru) into SQLite."""
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.db_manager import create_database, get_db_path, init_fts
from shared.help_parser import parse_help_sources


def import_help(root_path: Path, version: str, databases_dir: Path) -> tuple[bool, str]:
    """
    Import help from root_path (containing shcntx_ru, shlang_ru and/or shquery_ru) into DB.
    Returns (success, message).
    """
    root_path = root_path.resolve()
    shcntx = root_path / "shcntx_ru"
    shlang = root_path / "shlang_ru"
    shquery = root_path / "shquery_ru"

    if not shcntx.exists() and not shlang.exists() and not shquery.exists():
        return False, (
            f"В папке не найдены shcntx_ru, shlang_ru или shquery_ru: {root_path}"
        )

    db_path = get_db_path(databases_dir, version)
    conn = create_database(db_path, version)
    init_fts(conn)

    conn.execute("DELETE FROM syntax_methods")
    conn.execute("DELETE FROM syntax_objects")
    conn.execute("DELETE FROM help_search")
    conn.commit()

    try:
        count_objects = 0
        count_methods = 0
        count_query = 0

        for item in parse_help_sources(root_path):
            category = item.get("category", "object")
            is_query = category.startswith("query_")
            cursor = conn.execute(
                """INSERT INTO syntax_objects (name, full_name, category, parent_name, description, source)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    item.get("name", ""),
                    item.get("full_name"),
                    category,
                    item.get("parent_name"),
                    item.get("description"),
                    item.get("source", "shcntx_ru"),
                ),
            )
            obj_id = cursor.lastrowid
            count_objects += 1
            if is_query:
                count_query += 1
            full_name = item.get("full_name") or item.get("name", "")
            topic_id = item.get("parent_name") or ""

            for m in item.get("methods", []):
                cursor = conn.execute(
                    """INSERT INTO syntax_methods (object_id, name, kind, signature, params_json, returns, description, example, source)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        obj_id,
                        m.get("name", ""),
                        m.get("kind", "Method"),
                        m.get("signature"),
                        json.dumps(m.get("params", []), ensure_ascii=False) if m.get("params") else None,
                        m.get("returns"),
                        m.get("description"),
                        m.get("example"),
                        m.get("source", "shcntx_ru"),
                    ),
                )
                mid = cursor.lastrowid
                count_methods += 1
                mname = m.get("name", "")
                if is_query:
                    fts_name = mname or item.get("name", "")
                    fts_full = topic_id or full_name
                else:
                    fts_full = f"{full_name}.{mname}" if full_name and mname else mname
                    fts_name = mname
                fts_desc = " ".join(
                    filter(None, [m.get("description") or "", m.get("example") or "", full_name if is_query else ""])
                )
                conn.execute(
                    """INSERT INTO help_search (rowid, name, full_name, signature, description)
                       VALUES (?, ?, ?, ?, ?)""",
                    (mid, fts_name, fts_full, m.get("signature") or "", fts_desc),
                )

        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            ("source_path", str(root_path)),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            ("has_query_help", "true" if count_query else "false"),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            ("query_topics_count", str(count_query)),
        )
        conn.commit()
        msg = f"Справка {version} загружена. Объектов: {count_objects}, методов: {count_methods}"
        if count_query:
            msg += f", тем запросов: {count_query}"
        return True, msg
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()
