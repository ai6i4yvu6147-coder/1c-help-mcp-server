"""SQLite storage for metadata constructor projects."""
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path

IDENTIFIER_RE = re.compile(r"^[\w\u0400-\u04FF][\w\u0400-\u04FF0-9]*$", re.UNICODE)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS processor (
    name TEXT PRIMARY KEY,
    synonym_ru TEXT NOT NULL,
    form_name TEXT NOT NULL DEFAULT 'Форма',
    form_synonym_ru TEXT,
    attributes_json TEXT NOT NULL DEFAULT '[]',
    form_fields_json TEXT NOT NULL DEFAULT '[]',
    form_groups_json TEXT NOT NULL DEFAULT '[]',
    form_commands_json TEXT NOT NULL DEFAULT '[]',
    form_events_json TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS module (
    processor_name TEXT NOT NULL REFERENCES processor(name) ON DELETE CASCADE,
    module_key TEXT NOT NULL,
    code TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (processor_name, module_key)
);
"""

VALID_MODULE_KEYS = frozenset({"ObjectModule", "FormModule"})


def validate_identifier(name: str) -> str | None:
    """Return error message if name is not a valid 1C identifier, else None."""
    if not name:
        return "имя не может быть пустым"
    if not IDENTIFIER_RE.match(name):
        return f"недопустимое имя «{name}» (ожидается идентификатор 1С)"
    return None


def open_db(db_path: Path) -> sqlite3.Connection:
    """Open or create constructor.db with schema."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn


def _now() -> str:
    return datetime.now().isoformat()


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    for key in (
        "attributes_json",
        "form_fields_json",
        "form_groups_json",
        "form_commands_json",
        "form_events_json",
    ):
        d[key.replace("_json", "")] = json.loads(d.pop(key))
    return d


def create_processor(conn: sqlite3.Connection, name: str, synonym_ru: str) -> dict:
    err = validate_identifier(name)
    if err:
        raise ValueError(err)
    if not synonym_ru:
        raise ValueError("синоним не может быть пустым")
    existing = conn.execute(
        "SELECT 1 FROM processor WHERE name = ?", (name,)
    ).fetchone()
    if existing:
        raise ValueError(f"обработка «{name}» уже существует")
    now = _now()
    conn.execute(
        """INSERT INTO processor (name, synonym_ru, updated_at)
           VALUES (?, ?, ?)""",
        (name, synonym_ru, now),
    )
    conn.commit()
    return get_processor(conn, name)


def get_processor(conn: sqlite3.Connection, name: str) -> dict | None:
    row = conn.execute("SELECT * FROM processor WHERE name = ?", (name,)).fetchone()
    if not row:
        return None
    proc = _row_to_dict(row)
    modules = conn.execute(
        "SELECT module_key, code FROM module WHERE processor_name = ?",
        (name,),
    ).fetchall()
    proc["modules"] = {r["module_key"]: r["code"] for r in modules}
    return proc


def set_attributes(conn: sqlite3.Connection, name: str, attributes: list) -> dict:
    if get_processor(conn, name) is None:
        raise ValueError(f"обработка «{name}» не найдена")
    for attr in attributes:
        err = validate_identifier(attr.get("name", ""))
        if err:
            raise ValueError(f"реквизит: {err}")
        if not attr.get("type_raw"):
            raise ValueError(f"реквизит «{attr.get('name')}»: type_raw обязателен")
    conn.execute(
        "UPDATE processor SET attributes_json = ?, updated_at = ? WHERE name = ?",
        (json.dumps(attributes, ensure_ascii=False), _now(), name),
    )
    conn.commit()
    return get_processor(conn, name)


def set_form(
    conn: sqlite3.Connection,
    name: str,
    fields: list | None = None,
    groups: list | None = None,
    commands: list | None = None,
    events: list | None = None,
) -> dict:
    if get_processor(conn, name) is None:
        raise ValueError(f"обработка «{name}» не найдена")
    fields = fields if fields is not None else []
    groups = groups if groups is not None else []
    commands = commands if commands is not None else []
    events = events if events is not None else []
    conn.execute(
        """UPDATE processor SET
           form_fields_json = ?,
           form_groups_json = ?,
           form_commands_json = ?,
           form_events_json = ?,
           updated_at = ?
           WHERE name = ?""",
        (
            json.dumps(fields, ensure_ascii=False),
            json.dumps(groups, ensure_ascii=False),
            json.dumps(commands, ensure_ascii=False),
            json.dumps(events, ensure_ascii=False),
            _now(),
            name,
        ),
    )
    conn.commit()
    return get_processor(conn, name)


def set_module_code(
    conn: sqlite3.Connection, name: str, module_key: str, code: str
) -> dict:
    if get_processor(conn, name) is None:
        raise ValueError(f"обработка «{name}» не найдена")
    if module_key not in VALID_MODULE_KEYS:
        raise ValueError(
            f"модуль «{module_key}» не поддерживается (ожидается ObjectModule или FormModule)"
        )
    conn.execute(
        """INSERT INTO module (processor_name, module_key, code)
           VALUES (?, ?, ?)
           ON CONFLICT(processor_name, module_key) DO UPDATE SET code = excluded.code""",
        (name, module_key, code),
    )
    conn.execute(
        "UPDATE processor SET updated_at = ? WHERE name = ?",
        (_now(), name),
    )
    conn.commit()
    return get_processor(conn, name)
