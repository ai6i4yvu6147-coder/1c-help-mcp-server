"""Import help from unpacked HBK (shcntx_ru, shlang_ru) into SQLite."""
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.db_manager import create_database, get_db_path, init_fts
from shared.help_parser import parse_help_sources


def import_help(root_path: Path, version: str, databases_dir: Path) -> tuple[bool, str]:
    """
    Import help from root_path (containing shcntx_ru and/or shlang_ru) into DB.
    Returns (success, message).
    """
    root_path = root_path.resolve()
    shcntx = root_path / "shcntx_ru"
    shlang = root_path / "shlang_ru"

    if not shcntx.exists() and not shlang.exists():
        return False, f"В папке не найдены shcntx_ru или shlang_ru: {root_path}"

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

        for item in parse_help_sources(root_path):
            cursor = conn.execute(
                """INSERT INTO syntax_objects (name, full_name, category, description, source)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    item.get("name", ""),
                    item.get("full_name"),
                    item.get("category", "object"),
                    item.get("description"),
                    item.get("source", "shcntx_ru"),
                ),
            )
            obj_id = cursor.lastrowid
            count_objects += 1
            full_name = item.get("full_name") or item.get("name", "")

            for m in item.get("methods", []):
                cursor = conn.execute(
                    """INSERT INTO syntax_methods (object_id, name, kind, signature, params_json, returns, description, source)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        obj_id,
                        m.get("name", ""),
                        m.get("kind", "Method"),
                        m.get("signature"),
                        json.dumps(m.get("params", []), ensure_ascii=False) if m.get("params") else None,
                        m.get("returns"),
                        m.get("description"),
                        m.get("source", "shcntx_ru"),
                    ),
                )
                mid = cursor.lastrowid
                count_methods += 1
                mname = m.get("name", "")
                mfull = f"{full_name}.{mname}" if full_name and mname else mname
                conn.execute(
                    """INSERT INTO help_search (rowid, name, full_name, signature, description)
                       VALUES (?, ?, ?, ?, ?)""",
                    (mid, mname, mfull, m.get("signature") or "", m.get("description") or ""),
                )

        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            ("source_path", str(root_path)),
        )
        conn.commit()
        return True, f"Справка {version} загружена. Объектов: {count_objects}, методов: {count_methods}"
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()
