"""MCP tools for 1C syntax help."""
import json
import re
import sqlite3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.version_resolver import resolve_db_path, get_available_versions


class HelpTools:
    """Tools for querying 1C syntax help."""

    def __init__(self, databases_dir: str | Path, default_version: str | None = None):
        self.databases_dir = Path(databases_dir)
        self.default_version = default_version
        self._conn = None
        self._current_db = None

    def _get_connection(self, version: str | None = None) -> sqlite3.Connection | None:
        """Get connection to appropriate DB. Reuses if same version."""
        db_path = resolve_db_path(
            self.databases_dir, version, self.default_version
        )
        if not db_path or not db_path.exists():
            return None
        if self._current_db != db_path:
            if self._conn:
                self._conn.close()
            self._conn = sqlite3.connect(str(db_path))
            self._conn.row_factory = sqlite3.Row
            self._current_db = db_path
        return self._conn

    def list_versions(self) -> list[str]:
        """List available help versions."""
        return [v for v, _ in get_available_versions(self.databases_dir)]

    def get_syntax(self, name: str, version: str | None = None) -> dict | None:
        """
        Universal lookup: method, property, type, structure, global function.
        Returns dict with text, structured (signature, params, returns), or None.
        """
        conn = self._get_connection(version)
        if not conn:
            return None

        # Object/type/structure: syntax_objects + optional methods (для типов — данные в первом методе)
        cursor = conn.execute(
            f"""SELECT id, name, full_name, description FROM syntax_objects
                WHERE (name = ? OR full_name = ?) AND category NOT LIKE 'query_%'
                LIMIT 1""",
            (name, name)
        )
        row = cursor.fetchone()
        if row:
            text = row["description"] or ""
            sig, params, ret = None, [], None
            cursor = conn.execute(
                """SELECT signature, params_json, returns, description FROM syntax_methods
                   WHERE object_id = ? LIMIT 1""",
                (row["id"],),
            )
            mrow = cursor.fetchone()
            if mrow:
                sig = mrow["signature"]
                params = json.loads(mrow["params_json"]) if mrow["params_json"] else []
                ret = mrow["returns"]
                if mrow["description"] and not text:
                    text = mrow["description"]
            if not text:
                text = f"Найдено: {row['full_name'] or row['name']}"
            return {
                "text": text,
                "structured": {
                    "name": row["full_name"] or row["name"],
                    "signature": sig,
                    "params": params,
                    "returns": ret,
                }
            }

        # Try as method/property name (e.g. global function "Сообщить")
        cursor = conn.execute(
            f"""SELECT o.name as obj_name, o.full_name as obj_full, m.name, m.signature, m.params_json, m.returns, m.description
               FROM syntax_methods m
               JOIN syntax_objects o ON m.object_id = o.id
               WHERE m.name = ? AND {self._BSL_CATEGORY_FILTER}
               ORDER BY
                 CASE WHEN o.name = 'Глобальный контекст' THEN 0 ELSE 1 END,
                 CASE WHEN m.description IS NOT NULL AND m.description != '' THEN 0 ELSE 1 END,
                 CASE WHEN m.signature IS NOT NULL AND m.signature != '' THEN 0 ELSE 1 END
               LIMIT 1""",
            (name,)
        )
        row = cursor.fetchone()
        if row:
            params = json.loads(row["params_json"]) if row["params_json"] else []
            full = f"{row['obj_full'] or row['obj_name']}.{row['name']}" if row["obj_name"] else row["name"]
            return {
                "text": row["description"] or row["signature"] or "",
                "structured": {
                    "name": full,
                    "signature": row["signature"],
                    "params": params,
                    "returns": row["returns"],
                }
            }

        # Try Object.Method format
        if "." in name:
            parts = name.split(".", 1)
            obj_name, method_name = parts[0], parts[1]
            cursor = conn.execute(
                f"""SELECT m.name, m.signature, m.params_json, m.returns, m.description
                   FROM syntax_methods m
                   JOIN syntax_objects o ON m.object_id = o.id
                   WHERE (o.name = ? OR o.full_name = ?) AND m.name = ? AND {self._BSL_CATEGORY_FILTER}
                   LIMIT 1""",
                (obj_name, obj_name, method_name)
            )
            row = cursor.fetchone()
            if row:
                params = json.loads(row["params_json"]) if row["params_json"] else []
                return {
                    "text": row["description"] or row["signature"] or "",
                    "structured": {
                        "name": f"{obj_name}.{row['name']}",
                        "signature": row["signature"],
                        "params": params,
                        "returns": row["returns"],
                    }
                }

        return None

    _GLOBAL_CONTEXT = "Глобальный контекст"
    _BSL_CATEGORY_FILTER = "o.category NOT LIKE 'query_%'"
    _QUERY_CATEGORY_FILTER = "o.category LIKE 'query_%'"
    _QUERY_CATEGORY_MAP = {
        "keyword": "query_keyword",
        "function": "query_function",
        "statement": "query_statement",
        "operator": "query_operator",
        "literal": "query_literal",
        "article": "query_article",
    }

    def _query_category_filter(self, category: str | None) -> str | None:
        if not category:
            return None
        return self._QUERY_CATEGORY_MAP.get(category, f"query_{category}")

    _QUERY_TITLE_PREFIX = {
        "query_keyword": "Ключевое слово",
        "query_function": "Функция",
        "query_statement": "Предложение",
        "query_operator": "Оператор",
        "query_literal": "Литерал",
        "query_article": "",
    }

    def _query_title(self, obj_row) -> str:
        category = obj_row["category"] or ""
        if category == "query_article":
            return obj_row["full_name"] or obj_row["name"] or ""
        prefix = self._QUERY_TITLE_PREFIX.get(category, "")
        name = obj_row["name"] or ""
        return f"{prefix} {name}".strip() if prefix else name

    def _row_to_query_topic(self, obj_row, method_row) -> dict:
        see_also: list[str] = []
        if method_row and method_row["params_json"]:
            try:
                params = json.loads(method_row["params_json"])
                if params and isinstance(params[0], dict) and params[0].get("see_also"):
                    see_also = params[0]["see_also"]
            except (json.JSONDecodeError, IndexError, TypeError):
                pass

        return {
            "topic_id": obj_row["parent_name"] or obj_row["name"],
            "name": obj_row["name"],
            "category": obj_row["category"],
            "title": self._query_title(obj_row),
            "syntax": (method_row["signature"] if method_row else None) or "",
            "description": (method_row["description"] if method_row else None) or obj_row["description"] or "",
            "example": (method_row["example"] if method_row else None) or "",
            "see_also": see_also,
        }

    def get_query_syntax(self, name: str, version: str | None = None) -> dict | None:
        """Lookup query language topic by RU name, EN name or topic_id."""
        conn = self._get_connection(version)
        if not conn:
            return None

        name = name.strip()
        cursor = conn.execute(
            """SELECT o.id, o.name, o.full_name, o.parent_name, o.category, o.description
               FROM syntax_objects o
               WHERE o.category LIKE 'query_%'
                 AND (o.name = ? OR o.full_name = ? OR o.parent_name = ?)
               LIMIT 1""",
            (name, name, name),
        )
        obj_row = cursor.fetchone()
        if not obj_row:
            return None

        cursor = conn.execute(
            """SELECT signature, params_json, description, example
               FROM syntax_methods WHERE object_id = ? LIMIT 1""",
            (obj_row["id"],),
        )
        method_row = cursor.fetchone()
        return self._row_to_query_topic(obj_row, method_row)

    def search_query(
        self, query: str, version: str | None = None, max_results: int = 20
    ) -> list[dict]:
        """Full-text search within query language help only."""
        conn = self._get_connection(version)
        if not conn:
            return []

        query = query.strip()
        if not query:
            return []

        ranked: list[tuple[int, int, dict]] = []
        seen: set[int] = set()

        def _add_from_rows(rows, rank: int) -> None:
            for row in rows:
                rowid = row["rowid"]
                if rowid in seen:
                    continue
                seen.add(rowid)
                ranked.append((
                    rank,
                    len(row["full_name"] or row["name"] or ""),
                    {
                        "id": rowid,
                        "topic_id": row["topic_id"],
                        "name": row["name"],
                        "category": row["category"],
                        "signature": row["signature"],
                    },
                ))

        base_sql = f"""
            SELECT h.rowid, h.name, h.full_name, h.signature,
                   o.parent_name AS topic_id, o.category
            FROM help_search h
            JOIN syntax_methods m ON m.id = h.rowid
            JOIN syntax_objects o ON o.id = m.object_id
            WHERE {self._QUERY_CATEGORY_FILTER}
        """

        _add_from_rows(
            conn.execute(
                base_sql + " AND h.name = ? LIMIT ?",
                (query, max_results),
            ),
            0,
        )
        _add_from_rows(
            conn.execute(
                base_sql + " AND o.parent_name = ? LIMIT ?",
                (query, max_results),
            ),
            0,
        )
        _add_from_rows(
            conn.execute(
                base_sql + " AND h.full_name = ? LIMIT ?",
                (query, max_results),
            ),
            1,
        )

        fts_prefix = query.replace('"', '""')
        for fts_query in (
            f'name:"{fts_prefix}"',
            f'full_name:"{fts_prefix}"*',
        ):
            try:
                _add_from_rows(
                    conn.execute(
                        base_sql + " AND h MATCH ? LIMIT ?",
                        (fts_query, max_results),
                    ),
                    2,
                )
            except sqlite3.OperationalError:
                pass

        if len(ranked) < max_results:
            try:
                _add_from_rows(
                    conn.execute(
                        base_sql + " AND h MATCH ? LIMIT ?",
                        (query, max_results * 3),
                    ),
                    3,
                )
            except sqlite3.OperationalError:
                pass

        ranked.sort(key=lambda item: (item[0], item[1]))
        return [item[2] for item in ranked[:max_results]]

    def list_query_topics(
        self, category: str | None = None, version: str | None = None
    ) -> list[dict]:
        """List query language topics, optionally filtered by subcategory."""
        conn = self._get_connection(version)
        if not conn:
            return []

        db_category = self._query_category_filter(category)
        if db_category:
            cursor = conn.execute(
                """SELECT parent_name, name, description, category
                   FROM syntax_objects
                   WHERE category = ?
                   ORDER BY name""",
                (db_category,),
            )
        else:
            cursor = conn.execute(
                """SELECT parent_name, name, description, category
                   FROM syntax_objects
                   WHERE category LIKE 'query_%'
                   ORDER BY category, name"""
            )

        return [
            {
                "topic_id": row["parent_name"] or row["name"],
                "name": row["name"],
                "title": self._query_title(row),
                "category": row["category"],
            }
            for row in cursor.fetchall()
        ]

    def search_syntax(
        self, query: str, version: str | None = None, max_results: int = 20
    ) -> list[dict]:
        """Full-text BSL search (excludes query language topics)."""
        conn = self._get_connection(version)
        if not conn:
            return []

        query = query.strip()
        if not query:
            return []

        ranked: list[tuple[int, int, dict]] = []
        seen: set[int] = set()

        def _add_from_rows(rows, rank: int) -> None:
            for row in rows:
                rowid = row["rowid"]
                if rowid in seen:
                    continue
                seen.add(rowid)
                ranked.append((
                    rank,
                    len(row["full_name"] or row["name"] or ""),
                    {
                        "id": rowid,
                        "name": row["name"],
                        "full_name": row["full_name"],
                        "signature": row["signature"],
                    },
                ))

        base_sql = f"""
            SELECT h.rowid, h.name, h.full_name, h.signature
            FROM help_search h
            JOIN syntax_methods m ON m.id = h.rowid
            JOIN syntax_objects o ON o.id = m.object_id
            WHERE {self._BSL_CATEGORY_FILTER}
        """

        _add_from_rows(
            conn.execute(
                base_sql + " AND h.name = ? LIMIT ?",
                (query, max_results),
            ),
            0,
        )

        suffix = f".{query}"
        _add_from_rows(
            conn.execute(
                base_sql + " AND (h.full_name = ? OR h.full_name LIKE '%' || ?) LIMIT ?",
                (query, suffix, max_results),
            ),
            1,
        )

        fts_prefix = query.replace('"', '""')
        for fts_query in (
            f'name:"{fts_prefix}"',
            f'full_name:"{fts_prefix}"*',
        ):
            try:
                _add_from_rows(
                    conn.execute(
                        base_sql + " AND h MATCH ? LIMIT ?",
                        (fts_query, max_results),
                    ),
                    2,
                )
            except sqlite3.OperationalError:
                pass

        if len(ranked) < max_results:
            try:
                _add_from_rows(
                    conn.execute(
                        base_sql + " AND h MATCH ? LIMIT ?",
                        (query, max_results * 3),
                    ),
                    3,
                )
            except sqlite3.OperationalError:
                pass

        ranked.sort(key=lambda item: (item[0], item[1]))
        return [item[2] for item in ranked[:max_results]]

    # Коллекции метаданных → соответствующий менеджер (для Справочники.Х.Метод())
    _METADATA_TO_MANAGER = {
        "Справочники": "СправочникМенеджер",
        "Документы": "ДокументМенеджер",
        "Перечисления": "ПеречислениеМенеджер",
        "ПланыВидовХарактеристик": "ПланВидовХарактеристикМенеджер",
        "ПланыСчетов": "ПланСчетовМенеджер",
        "ПланыВидовРасчета": "ПланВидовРасчетаМенеджер",
        "БизнесПроцессы": "БизнесПроцессМенеджер",
        "Задачи": "ЗадачаМенеджер",
        "РегистрыСведений": "РегистрСведенийМенеджер",
        "РегистрыНакопления": "РегистрНакопленияМенеджер",
        "РегистрыБухгалтерии": "РегистрБухгалтерииМенеджер",
        "Отчеты": "ОтчетМенеджер",
        "Обработки": "ОбработкаМенеджер",
    }

    def get_object_api(self, object_name: str, version: str | None = None) -> dict | None:
        """Methods, properties, events of object."""
        conn = self._get_connection(version)
        if not conn:
            return None

        # Справочники.Х → СправочникМенеджер
        lookup = object_name.split(".")[0] if "." in object_name else object_name
        object_name = self._METADATA_TO_MANAGER.get(lookup, object_name)

        cursor = conn.execute(
            f"""SELECT id FROM syntax_objects
                WHERE (name = ? OR full_name = ?) AND category NOT LIKE 'query_%'
                LIMIT 1""",
            (object_name, object_name)
        )
        row = cursor.fetchone()
        # Fallback: шаблонные объекты (СправочникМенеджер.<Имя справочника>)
        if not row:
            cursor = conn.execute(
                f"""SELECT id FROM syntax_objects
                    WHERE full_name LIKE ? AND category NOT LIKE 'query_%'
                    ORDER BY length(full_name) LIMIT 1""",
                (object_name + ".%",)
            )
            row = cursor.fetchone()
        if not row:
            return None

        cursor = conn.execute(
            """SELECT name, kind, signature FROM syntax_methods
               WHERE object_id = ? ORDER BY kind, name""",
            (row["id"],)
        )
        items = [{"name": r["name"], "kind": r["kind"], "signature": r["signature"]} for r in cursor.fetchall()]

        # Fallback: если методов нет по object_id — берём из help_search по full_name Object.*
        # (прямые члены: Object.Method и Object.Property.SubMember -> Method/Property)
        if not items:
            prefix = f"{object_name}."
            cursor = conn.execute(
                f"""SELECT h.full_name, m.name, m.kind, m.signature
                   FROM help_search h
                   JOIN syntax_methods m ON m.id = h.rowid
                   JOIN syntax_objects o ON o.id = m.object_id
                   WHERE h.full_name LIKE ? AND {self._BSL_CATEGORY_FILTER}""",
                (prefix + "%",),
            )
            seen = set()
            for r in cursor.fetchall():
                fn = r["full_name"] or ""
                rest = fn[len(prefix) :] if fn.startswith(prefix) else ""
                direct = rest.split(".")[0].strip()
                if direct and direct not in seen:
                    seen.add(direct)
                    items.append(
                        {"name": direct, "kind": r["kind"] or "Method", "signature": r["signature"]}
                    )
            items.sort(key=lambda x: (x["kind"] or "", x["name"]))

        return {"object": object_name, "methods": items}

    def list_syntax(
        self, category: str | None = None, version: str | None = None
    ) -> list[dict]:
        """List objects by category: object, type, structure, operator, global."""
        conn = self._get_connection(version)
        if not conn:
            return []

        if category == "global":
            cursor = conn.execute(
                """SELECT m.name, o.full_name || '.' || m.name AS full_name, 'global' AS category
                   FROM syntax_methods m
                   JOIN syntax_objects o ON m.object_id = o.id
                   WHERE o.name = ?
                   ORDER BY m.name""",
                (self._GLOBAL_CONTEXT,),
            )
            return [dict(row) for row in cursor.fetchall()]

        db_category = "structure" if category == "operator" else category
        if db_category:
            cursor = conn.execute(
                "SELECT name, full_name, category FROM syntax_objects WHERE category = ? ORDER BY name",
                (db_category,),
            )
        else:
            cursor = conn.execute(
                "SELECT name, full_name, category FROM syntax_objects WHERE category NOT LIKE 'query_%' ORDER BY category, name"
            )
        return [dict(row) for row in cursor.fetchall()]

    def validate_code(
        self, code: str, version: str | None = None, max_errors: int = 50
    ) -> list[dict]:
        """
        Проверка кода 1С: поиск вызовов .Метод(), которых нет в API объекта.
        Возвращает список {object, method, line, suggestion} для каждой предполагаемой ошибки.
        """
        conn = self._get_connection(version)
        if not conn:
            return []

        def _ru_key(n: str) -> str:
            return n.split("(")[0].strip() if n else ""

        errors = []
        lines = code.splitlines()
        # Ищем вызовы Объект.Метод( — идентификаторы: буквы, цифры, подчёркивание, точка
        pattern = re.compile(
            r"([\w\u0400-\u04FF]+(?:\.[\w\u0400-\u04FF]+)*)\.([\w\u0400-\u04FF]+)\s*\(",
            re.UNICODE,
        )
        seen = set()

        for line_no, line in enumerate(lines, 1):
            for m in pattern.finditer(line):
                obj_part, method_name = m.group(1), m.group(2)
                # Пропускаем типичные не-объекты
                if method_name in ("ЗначениеЗаполнено", "ТипЗнч", "Формат") and "." not in obj_part:
                    continue
                key = (line_no, obj_part, method_name)
                if key in seen:
                    continue
                seen.add(key)

                # Определяем API-объект
                first = obj_part.split(".")[0]
                api_obj = self._METADATA_TO_MANAGER.get(first, obj_part)

                api = self.get_object_api(api_obj, version)
                if not api:
                    errors.append({
                        "object": obj_part,
                        "method": method_name,
                        "line": line_no,
                        "kind": "unknown_object",
                        "message": f"объект «{obj_part}» не найден в справке",
                    })
                    if len(errors) >= max_errors:
                        return errors
                    continue

                methods = {_ru_key(x["name"]) for x in api.get("methods", [])}
                if _ru_key(method_name) not in methods:
                    suggestion_list = []
                    for mn in methods:
                        if method_name.lower() in mn.lower() or mn.lower() in method_name.lower():
                            suggestion_list.append(mn)
                    suggestion = " или ".join(suggestion_list[:3]) if suggestion_list else "проверьте список методов объекта"
                    errors.append({
                        "object": obj_part,
                        "method": method_name,
                        "line": line_no,
                        "kind": "invalid_method",
                        "api_object": api.get("object", api_obj),
                        "suggestion": suggestion or "проверьте список методов объекта",
                    })
                    if len(errors) >= max_errors:
                        return errors

        return errors
