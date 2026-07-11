"""MCP tools for metadata constructor (external data processors and reports)."""
from pathlib import Path

from shared.constructor import db as constructor_db
from shared.constructor.export import export_project as do_export_processor
from shared.constructor.export_report import export_report as do_export_report
from shared.constructor.validate import validate_project as do_validate_processor
from shared.constructor.validate_report import validate_report as do_validate_report


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

    def create_report(self, name: str, synonym: str, kind: str = "skd") -> dict:
        conn = self._get_connection()
        report = constructor_db.create_report(conn, name, synonym, kind=kind)
        return {"name": report["name"], "synonym_ru": report["synonym_ru"], "kind": report["kind"]}

    def set_report_skd(
        self,
        report: str,
        query: str | None = None,
        fields: list | None = None,
        parameters: list | None = None,
        calculated_fields: list | None = None,
        totals: list | None = None,
        layout: dict | None = None,
    ) -> dict:
        conn = self._get_connection()
        result = constructor_db.set_report_skd(
            conn,
            report,
            query=query,
            fields=fields,
            parameters=parameters,
            calculated_fields=calculated_fields,
            totals=totals,
            layout=layout,
        )
        return {
            "name": result["name"],
            "field_count": len(result.get("fields") or []),
            "has_layout": bool(result.get("layout")),
        }

    def set_report_attributes(self, report: str, attributes: list) -> dict:
        conn = self._get_connection()
        result = constructor_db.set_report_attributes(conn, report, attributes)
        return {"name": result["name"], "attributes": result["attributes"]}

    def set_report_tabular_sections(self, report: str, tabular_sections: list) -> dict:
        conn = self._get_connection()
        result = constructor_db.set_report_tabular_sections(conn, report, tabular_sections)
        return {"name": result["name"], "tabular_sections": result["tabular_sections"]}

    def set_report_form(
        self,
        report: str,
        form_name: str | None = None,
        form_synonym: str | None = None,
        fields: list | None = None,
        groups: list | None = None,
        commands: list | None = None,
        events: list | None = None,
        spreadsheet_fields: list | None = None,
    ) -> dict:
        conn = self._get_connection()
        result = constructor_db.set_report_form(
            conn,
            report,
            form_name=form_name,
            form_synonym_ru=form_synonym,
            fields=fields,
            groups=groups,
            commands=commands,
            events=events,
            spreadsheet_fields=spreadsheet_fields,
        )
        return {
            "name": result["name"],
            "form_name": result["form_name"],
            "form_fields": result["form_fields"],
            "form_groups": result["form_groups"],
            "form_commands": result["form_commands"],
            "form_events": result["form_events"],
            "form_spreadsheet_fields": result["form_spreadsheet_fields"],
        }

    def set_report_template(
        self, report: str, areas: list, template_name: str | None = None
    ) -> dict:
        conn = self._get_connection()
        result = constructor_db.set_report_template(
            conn, report, areas, template_name=template_name
        )
        return {
            "name": result["name"],
            "template_name": result["template_name"],
            "area_count": len(result.get("template_areas") or []),
        }

    def set_report_module_code(self, report: str, code: str, module: str = "ObjectModule") -> dict:
        conn = self._get_connection()
        result = constructor_db.set_report_module_code(conn, report, module, code)
        return {"name": result["name"], "module": module, "code_length": len(code)}

    def validate_report(self, report: str, version: str | None = None) -> dict:
        conn = self._get_connection()
        row = constructor_db.get_report(conn, report)
        if row is None:
            raise ValueError(f"отчёт «{report}» не найден")
        return do_validate_report(row, self.help_tools, version)

    def export_report(self, report: str, path: str) -> dict:
        conn = self._get_connection()
        row = constructor_db.get_report(conn, report)
        if row is None:
            raise ValueError(f"отчёт «{report}» не найден")
        return do_export_report(row, Path(path))

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
        return do_validate_processor(proc, self.help_tools, version)

    def export_project(self, processor: str, path: str) -> dict:
        conn = self._get_connection()
        proc = constructor_db.get_processor(conn, processor)
        if proc is None:
            raise ValueError(f"обработка «{processor}» не найдена")
        return do_export_processor(proc, Path(path))
