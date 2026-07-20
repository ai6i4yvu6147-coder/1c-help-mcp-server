"""Импорт справки 1С в SQLite.

Источник — папка, где лежат либо архивы .hbk (shcntx_ru.hbk, shlang_ru.hbk,
shquery_ru.hbk), либо уже распакованные каталоги с тем же именем. Архивы
распаковываются во временную папку автоматически — вручную разархивировать не нужно.
"""
import json
import shutil
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.db_manager import create_database, get_db_path, init_fts
from shared.help_parser import parse_help_sources
from shared.hbk_extractor import (
    HELP_SOURCES,
    extract_help_folder,
    find_help_archives,
)


def _has_unpacked_sources(root_path: Path) -> bool:
    return any((root_path / name).is_dir() for name in HELP_SOURCES)


def import_help(root_path: Path, version: str, databases_dir: Path) -> tuple[bool, str]:
    """
    Загрузить справку из root_path в БД версии version.

    root_path может содержать:
      * архивы .hbk (shcntx_ru.hbk, …) — распаковываются автоматически, либо
      * уже распакованные каталоги (shcntx_ru/, …).

    Возвращает (успех, сообщение).
    """
    root_path = root_path.resolve()
    tmp_dir: Path | None = None
    try:
        archives = find_help_archives(root_path)
        if archives:
            tmp_dir = Path(tempfile.mkdtemp(prefix="1c_help_hbk_"))
            extract_help_folder(root_path, tmp_dir)
            source_root = tmp_dir
        elif _has_unpacked_sources(root_path):
            source_root = root_path
        else:
            return False, (
                "В папке не найдены ни архивы (shcntx_ru.hbk, shlang_ru.hbk, "
                f"shquery_ru.hbk), ни распакованные каталоги: {root_path}"
            )
        return _build_database(source_root, root_path, version, databases_dir)
    finally:
        if tmp_dir is not None:
            shutil.rmtree(tmp_dir, ignore_errors=True)


def _build_database(
    source_root: Path, origin_path: Path, version: str, databases_dir: Path
) -> tuple[bool, str]:
    """Разобрать справку из source_root и записать в БД.

    origin_path сохраняется в meta.source_path (исходная папка пользователя —
    архивы или каталоги), чтобы «обновить из сохранённого источника» работало.
    """
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

        for item in parse_help_sources(source_root):
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
            ("source_path", str(origin_path)),
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
