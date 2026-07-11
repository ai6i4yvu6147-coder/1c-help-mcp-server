"""MCP tools for metadata constructor (external data processors)."""
from pathlib import Path

from shared.constructor import db as constructor_db
from shared.constructor.export import export_project as do_export
from shared.constructor.validate import validate_project as do_validate


class ConstructorTools:
    def __init__(self, constructor_db_path: str | Path, help_tools):
        self.db_path = Path(constructor_db_path)
        self.help_tools = help_tools
        self._conn = None

    def _get_connection(self):
        if self._conn is None:
            self._conn = constructor_db.open_db(self.db_path)
        return self._conn

    def create_processor(self, name: str, synonym: str) -> dict:
        conn = self._get_connection()
        proc = constructor_db.create_processor(conn, name, synonym)
        return {"name": proc["name"], "synonym_ru": proc["synonym_ru"]}

    def set_attributes(self, processor: str, attributes: list) -> dict:
        conn = self._get_connection()
        proc = constructor_db.set_attributes(conn, processor, attributes)
        return {"name": proc["name"], "attributes": proc["attributes"]}

    def set_form(
        self,
        processor: str,
        fields: list | None = None,
        groups: list | None = None,
        commands: list | None = None,
        events: list | None = None,
    ) -> dict:
        conn = self._get_connection()
        proc = constructor_db.set_form(
            conn, processor, fields=fields, groups=groups, commands=commands, events=events
        )
        return {
            "name": proc["name"],
            "form_fields": proc["form_fields"],
            "form_groups": proc["form_groups"],
            "form_commands": proc["form_commands"],
            "form_events": proc["form_events"],
        }

    def set_module_code(self, processor: str, module: str, code: str) -> dict:
        conn = self._get_connection()
        proc = constructor_db.set_module_code(conn, processor, module, code)
        return {"name": proc["name"], "module": module, "code_length": len(code)}

    def validate_project(self, processor: str, version: str | None = None) -> dict:
        conn = self._get_connection()
        proc = constructor_db.get_processor(conn, processor)
        if proc is None:
            raise ValueError(f"обработка «{processor}» не найдена")
        return do_validate(proc, self.help_tools, version)

    def export_project(self, processor: str, path: str) -> dict:
        conn = self._get_connection()
        proc = constructor_db.get_processor(conn, processor)
        if proc is None:
            raise ValueError(f"обработка «{processor}» не найдена")
        return do_export(proc, Path(path))
