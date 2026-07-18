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

CREATE TABLE IF NOT EXISTS report (
    name TEXT PRIMARY KEY,
    synonym_ru TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'skd',
    schema_name TEXT NOT NULL DEFAULT 'ОсновнаяСхемаКомпоновкиДанных',
    query_text TEXT NOT NULL DEFAULT '',
    fields_json TEXT NOT NULL DEFAULT '[]',
    datasets_json TEXT NOT NULL DEFAULT '[]',
    dataset_links_json TEXT NOT NULL DEFAULT '[]',
    parameters_json TEXT NOT NULL DEFAULT '[]',
    calculated_json TEXT NOT NULL DEFAULT '[]',
    totals_json TEXT NOT NULL DEFAULT '[]',
    layout_json TEXT NOT NULL DEFAULT '{}',
    attributes_json TEXT NOT NULL DEFAULT '[]',
    tabular_sections_json TEXT NOT NULL DEFAULT '[]',
    form_name TEXT NOT NULL DEFAULT 'Форма',
    form_synonym_ru TEXT,
    form_fields_json TEXT NOT NULL DEFAULT '[]',
    form_groups_json TEXT NOT NULL DEFAULT '[]',
    form_commands_json TEXT NOT NULL DEFAULT '[]',
    form_events_json TEXT NOT NULL DEFAULT '[]',
    form_spreadsheet_fields_json TEXT NOT NULL DEFAULT '[]',
    template_name TEXT NOT NULL DEFAULT 'Макет',
    template_areas_json TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS report_module (
    report_name TEXT NOT NULL REFERENCES report(name) ON DELETE CASCADE,
    module_key TEXT NOT NULL DEFAULT 'ObjectModule',
    code TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (report_name, module_key)
);
"""

VALID_MODULE_KEYS = frozenset({"ObjectModule", "FormModule"})
VALID_REPORT_MODULE_KEYS = frozenset({"ObjectModule", "FormModule"})
VALID_REPORT_KINDS = frozenset({"skd", "macet"})


def validate_identifier(name: str) -> str | None:
    """Return error message if name is not a valid 1C identifier, else None."""
    if not name:
        return "имя не может быть пустым"
    if not IDENTIFIER_RE.match(name):
        return f"недопустимое имя «{name}» (ожидается идентификатор 1С)"
    return None


# Columns added to `report` after the initial schema shipped. `CREATE TABLE IF NOT EXISTS`
# never alters an existing table, so add them on open for DBs created before they existed.
_REPORT_ADDED_COLUMNS = {
    "datasets_json": "TEXT NOT NULL DEFAULT '[]'",
    "dataset_links_json": "TEXT NOT NULL DEFAULT '[]'",
}


def _ensure_report_columns(conn: sqlite3.Connection) -> None:
    existing = {r["name"] for r in conn.execute("PRAGMA table_info(report)")}
    for column, decl in _REPORT_ADDED_COLUMNS.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE report ADD COLUMN {column} {decl}")
    conn.commit()


def open_db(db_path: Path) -> sqlite3.Connection:
    """Open or create constructor.db with schema."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    _ensure_report_columns(conn)
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


def _report_row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    for key in (
        "fields_json",
        "datasets_json",
        "dataset_links_json",
        "parameters_json",
        "calculated_json",
        "totals_json",
        "layout_json",
        "attributes_json",
        "tabular_sections_json",
        "form_fields_json",
        "form_groups_json",
        "form_commands_json",
        "form_events_json",
        "form_spreadsheet_fields_json",
        "template_areas_json",
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


def create_report(
    conn: sqlite3.Connection, name: str, synonym_ru: str, kind: str = "skd"
) -> dict:
    err = validate_identifier(name)
    if err:
        raise ValueError(err)
    if not synonym_ru:
        raise ValueError("синоним не может быть пустым")
    if kind not in VALID_REPORT_KINDS:
        raise ValueError(f"kind «{kind}» не поддерживается (ожидается skd или macet)")
    existing = conn.execute("SELECT 1 FROM report WHERE name = ?", (name,)).fetchone()
    if existing:
        raise ValueError(f"отчёт «{name}» уже существует")
    now = _now()
    conn.execute(
        """INSERT INTO report (name, synonym_ru, kind, updated_at)
           VALUES (?, ?, ?, ?)""",
        (name, synonym_ru, kind, now),
    )
    conn.commit()
    return get_report(conn, name)


def get_report(conn: sqlite3.Connection, name: str) -> dict | None:
    row = conn.execute("SELECT * FROM report WHERE name = ?", (name,)).fetchone()
    if not row:
        return None
    report = _report_row_to_dict(row)
    modules = conn.execute(
        "SELECT module_key, code FROM report_module WHERE report_name = ?",
        (name,),
    ).fetchall()
    report["modules"] = {r["module_key"]: r["code"] for r in modules}
    return report


def set_report_skd(
    conn: sqlite3.Connection,
    name: str,
    *,
    query: str | None = None,
    fields: list | None = None,
    datasets: list | None = None,
    dataset_links: list | None = None,
    parameters: list | None = None,
    calculated_fields: list | None = None,
    totals: list | None = None,
    layout: dict | None = None,
) -> dict:
    if get_report(conn, name) is None:
        raise ValueError(f"отчёт «{name}» не найден")
    updates = []
    values: list = []
    if query is not None:
        updates.append("query_text = ?")
        values.append(query)
    if fields is not None:
        for field in fields:
            if not field.get("data_path"):
                raise ValueError("поле набора данных: data_path обязателен")
        updates.append("fields_json = ?")
        values.append(json.dumps(fields, ensure_ascii=False))
    if datasets is not None:
        for ds in datasets:
            err = validate_identifier(ds.get("name", ""))
            if err:
                raise ValueError(f"набор данных: {err}")
            for field in ds.get("fields") or []:
                if not field.get("data_path"):
                    raise ValueError(f"набор «{ds.get('name')}»: поле без data_path")
        updates.append("datasets_json = ?")
        values.append(json.dumps(datasets, ensure_ascii=False))
    if dataset_links is not None:
        updates.append("dataset_links_json = ?")
        values.append(json.dumps(dataset_links, ensure_ascii=False))
    if parameters is not None:
        updates.append("parameters_json = ?")
        values.append(json.dumps(parameters, ensure_ascii=False))
    if calculated_fields is not None:
        updates.append("calculated_json = ?")
        values.append(json.dumps(calculated_fields, ensure_ascii=False))
    if totals is not None:
        updates.append("totals_json = ?")
        values.append(json.dumps(totals, ensure_ascii=False))
    if layout is not None:
        updates.append("layout_json = ?")
        values.append(json.dumps(layout, ensure_ascii=False))
    if not updates:
        raise ValueError("нечего обновлять: укажите query, fields, layout и/или другие секции СКД")
    updates.append("updated_at = ?")
    values.append(_now())
    values.append(name)
    conn.execute(
        f"UPDATE report SET {', '.join(updates)} WHERE name = ?",
        values,
    )
    conn.commit()
    return get_report(conn, name)


def set_report_attributes(
    conn: sqlite3.Connection, name: str, attributes: list
) -> dict:
    """Object-level requisites for a layout ("macet") report, standing in for DCS
    parameters (confirmed real pattern on `ФТ_ОтчетБДР`: own `Attribute` children, no
    DCS at all). No-op for `kind='skd'` reports beyond storing the value -- export only
    reads this field for `kind='macet'`."""
    if get_report(conn, name) is None:
        raise ValueError(f"отчёт «{name}» не найден")
    for attr in attributes:
        err = validate_identifier(attr.get("name", ""))
        if err:
            raise ValueError(f"реквизит: {err}")
        if not attr.get("type_raw"):
            raise ValueError(f"реквизит «{attr.get('name')}»: type_raw обязателен")
    conn.execute(
        "UPDATE report SET attributes_json = ?, updated_at = ? WHERE name = ?",
        (json.dumps(attributes, ensure_ascii=False), _now(), name),
    )
    conn.commit()
    return get_report(conn, name)


def set_report_tabular_sections(
    conn: sqlite3.Connection, name: str, tabular_sections: list
) -> dict:
    """Table-part requisites for a layout report (e.g. a multi-select list of
    organizations/periods -- `Организации`/`ПериодыОтчета` on `ФТ_ОтчетБДР`).
    `tabular_sections`: `[{name, synonym_ru?, attributes: [{name, type_raw, ...}]}]`."""
    if get_report(conn, name) is None:
        raise ValueError(f"отчёт «{name}» не найден")
    for ts in tabular_sections:
        err = validate_identifier(ts.get("name", ""))
        if err:
            raise ValueError(f"табличная часть: {err}")
        for attr in ts.get("attributes") or []:
            err = validate_identifier(attr.get("name", ""))
            if err:
                raise ValueError(f"табличная часть «{ts.get('name')}», реквизит: {err}")
            if not attr.get("type_raw"):
                raise ValueError(
                    f"табличная часть «{ts.get('name')}», реквизит «{attr.get('name')}»: type_raw обязателен"
                )
    conn.execute(
        "UPDATE report SET tabular_sections_json = ?, updated_at = ? WHERE name = ?",
        (json.dumps(tabular_sections, ensure_ascii=False), _now(), name),
    )
    conn.commit()
    return get_report(conn, name)


def set_report_form(
    conn: sqlite3.Connection,
    name: str,
    form_name: str | None = None,
    form_synonym_ru: str | None = None,
    fields: list | None = None,
    groups: list | None = None,
    commands: list | None = None,
    events: list | None = None,
    spreadsheet_fields: list | None = None,
) -> dict:
    """Custom managed form for a layout report (mirrors `set_form` for processors --
    same `build_form_layout` shape, since `Forms/<name>/Ext/Form.xml` is identical
    between `ExternalReport` and `ExternalDataProcessor`).

    `spreadsheet_fields`: list of `{name, title_ru?, events?}` -- each becomes a
    `SpreadSheetDocumentField` bound to a form-level `mxl:SpreadsheetDocument` attribute
    (`build_spreadsheet_field`). This is the *only* way a macet report's form can
    actually display `ТабДок.Вывести(...)` output -- a plain `fields` entry would
    render as a text `InputField`, which cannot show a spreadsheet document."""
    report = get_report(conn, name)
    if report is None:
        raise ValueError(f"отчёт «{name}» не найден")
    updates = []
    values: list = []
    if form_name is not None:
        err = validate_identifier(form_name)
        if err:
            raise ValueError(f"имя формы: {err}")
        updates.append("form_name = ?")
        values.append(form_name)
    if form_synonym_ru is not None:
        updates.append("form_synonym_ru = ?")
        values.append(form_synonym_ru)
    if fields is not None:
        updates.append("form_fields_json = ?")
        values.append(json.dumps(fields, ensure_ascii=False))
    if groups is not None:
        updates.append("form_groups_json = ?")
        values.append(json.dumps(groups, ensure_ascii=False))
    if commands is not None:
        updates.append("form_commands_json = ?")
        values.append(json.dumps(commands, ensure_ascii=False))
    if events is not None:
        updates.append("form_events_json = ?")
        values.append(json.dumps(events, ensure_ascii=False))
    if spreadsheet_fields is not None:
        updates.append("form_spreadsheet_fields_json = ?")
        values.append(json.dumps(spreadsheet_fields, ensure_ascii=False))
    if not updates:
        raise ValueError(
            "нечего обновлять: укажите form_name, fields, groups, commands, events и/или spreadsheet_fields"
        )
    updates.append("updated_at = ?")
    values.append(_now())
    values.append(name)
    conn.execute(f"UPDATE report SET {', '.join(updates)} WHERE name = ?", values)
    conn.commit()
    return get_report(conn, name)


def set_report_template(
    conn: sqlite3.Connection,
    name: str,
    areas: list,
    template_name: str | None = None,
) -> dict:
    """Spreadsheet-document macet for a layout report: `areas` is
    `build_spreadsheet_template`-shaped, `[{name, rows: [[cell, ...], ...]}]`. Filled at
    runtime via `Макет.ПолучитьОбласть("Имя")` / `ТабДок.Вывести(Область, Уровень)` in
    hand-written module code (`set_report_module_code`) -- grouping/indentation is a BSL
    concern, not something this schema encodes."""
    if get_report(conn, name) is None:
        raise ValueError(f"отчёт «{name}» не найден")
    if not areas:
        raise ValueError("areas не может быть пустым")
    for area in areas:
        err = validate_identifier(area.get("name", ""))
        if err:
            raise ValueError(f"область макета: {err}")
        if not area.get("rows"):
            raise ValueError(f"область «{area.get('name')}»: rows не может быть пустым")
    updates = ["template_areas_json = ?"]
    values: list = [json.dumps(areas, ensure_ascii=False)]
    if template_name is not None:
        err = validate_identifier(template_name)
        if err:
            raise ValueError(f"имя макета: {err}")
        updates.append("template_name = ?")
        values.append(template_name)
    updates.append("updated_at = ?")
    values.append(_now())
    values.append(name)
    conn.execute(f"UPDATE report SET {', '.join(updates)} WHERE name = ?", values)
    conn.commit()
    return get_report(conn, name)


def set_report_module_code(
    conn: sqlite3.Connection, name: str, module_key: str, code: str
) -> dict:
    if get_report(conn, name) is None:
        raise ValueError(f"отчёт «{name}» не найден")
    if module_key not in VALID_REPORT_MODULE_KEYS:
        raise ValueError(
            f"модуль «{module_key}» не поддерживается для отчёта (ожидается ObjectModule или FormModule)"
        )
    conn.execute(
        """INSERT INTO report_module (report_name, module_key, code)
           VALUES (?, ?, ?)
           ON CONFLICT(report_name, module_key) DO UPDATE SET code = excluded.code""",
        (name, module_key, code),
    )
    conn.execute("UPDATE report SET updated_at = ? WHERE name = ?", (_now(), name))
    conn.commit()
    return get_report(conn, name)
