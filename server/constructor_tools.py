"""MCP tools for metadata constructor (external data processors and reports)."""
from pathlib import Path

from onec_metadata_schema.dcs import build_dcs_standard_period_params

from shared.constructor import db as constructor_db
from shared.constructor.export import export as do_export
from shared.constructor.validate import validate as do_validate


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
        datasets: list | None = None,
        dataset_links: list | None = None,
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
            datasets=datasets,
            dataset_links=dataset_links,
            parameters=parameters,
            calculated_fields=calculated_fields,
            totals=totals,
            layout=layout,
        )
        result_datasets = result.get("datasets") or []
        field_count = (
            sum(len(d.get("fields") or []) for d in result_datasets)
            if result_datasets else len(result.get("fields") or [])
        )
        return {
            "name": result["name"],
            "field_count": field_count,
            "dataset_count": len(result_datasets) or (1 if result.get("fields") else 0),
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

    # --- Unified surface (write-tools-taxonomy.md) ---------------------------------
    # Group by "unit of editing", not by object view or XML section. `project` is one
    # handle over the processor/report tables; `kind` is a parameter, not a tool family.
    # The typed setters above back these facades; `validate`/`export` call the single
    # kind-branching helpers in shared.constructor.{validate,export}.

    def _get_row(self, project: str, kind: str) -> dict:
        conn = self._get_connection()
        row = (constructor_db.get_processor(conn, project) if kind == "processor"
               else constructor_db.get_report(conn, project))
        if row is None:  # _resolve_kind already confirmed existence; defensive only
            raise ValueError(f"проект «{project}» не найден")
        return row

    def _resolve_kind(self, project: str) -> str:
        """'processor' | 'report' by looking the name up in both tables.

        Raises on miss, and on the ambiguous case where the same name exists in both
        tables (rare -- separate tables, but names could collide): the caller should use
        the old kind-specific tools to disambiguate rather than us guessing."""
        conn = self._get_connection()
        is_processor = constructor_db.get_processor(conn, project) is not None
        is_report = constructor_db.get_report(conn, project) is not None
        if is_processor and is_report:
            raise ValueError(
                f"«{project}» существует и как обработка, и как отчёт — неоднозначно; "
                f"используйте kind-специфичные tools (set_attributes / set_report_attributes)"
            )
        if is_processor:
            return "processor"
        if is_report:
            return "report"
        raise ValueError(f"проект «{project}» не найден (ни обработка, ни отчёт)")

    def create(self, kind: str, name: str, synonym: str, archetype: str | None = None) -> dict:
        """`create_processor` + `create_report` under one tool. `kind` is the object view
        (`processor` / `report`); `archetype` (`skd` / `macet`) applies to reports only and
        maps to the report's stored kind."""
        if kind == "processor":
            if archetype:
                raise ValueError("archetype применим только к kind=report")
            res = self.create_processor(name, synonym)
            return {"kind": "processor", **res}
        if kind == "report":
            res = self.create_report(name, synonym, kind=archetype or "skd")
            return {
                "kind": "report",
                "archetype": res["kind"],
                "name": res["name"],
                "synonym_ru": res["synonym_ru"],
            }
        raise ValueError(f"kind «{kind}» не поддерживается (ожидается processor или report)")

    def set_object(
        self,
        project: str,
        attributes: list | None = None,
        tabular_sections: list | None = None,
    ) -> dict:
        """Object shell (GUID layer): `set_attributes` + `set_report_attributes` +
        `set_report_tabular_sections`. One call = full replacement of the shell spec."""
        kind = self._resolve_kind(project)
        if kind == "processor":
            if tabular_sections:
                raise ValueError("табличные части не поддерживаются для обработки")
            if attributes is None:
                raise ValueError("укажите attributes")
            res = self.set_attributes(project, attributes)
            return {"kind": kind, **res}
        if attributes is None and tabular_sections is None:
            raise ValueError("укажите attributes и/или tabular_sections")
        out = {"kind": kind, "name": project}
        if attributes is not None:
            out["attributes"] = self.set_report_attributes(project, attributes)["attributes"]
        if tabular_sections is not None:
            out["tabular_sections"] = self.set_report_tabular_sections(
                project, tabular_sections
            )["tabular_sections"]
        return out

    def set_form_any(
        self,
        project: str,
        *,
        fields: list | None = None,
        groups: list | None = None,
        commands: list | None = None,
        events: list | None = None,
        spreadsheet_fields: list | None = None,
        form_name: str | None = None,
        form_synonym: str | None = None,
    ) -> dict:
        """Form (any element) for a processor or report: `set_form` + `set_report_form`.
        Processor forms don't carry a custom `form_name`/`spreadsheet_fields` (those are
        report-form concepts)."""
        kind = self._resolve_kind(project)
        if kind == "processor":
            if spreadsheet_fields or form_name or form_synonym:
                raise ValueError(
                    "для обработки поддержаны только fields/groups/commands/events"
                )
            res = self.set_form(
                project, fields=fields, groups=groups, commands=commands, events=events
            )
            return {"kind": kind, **res}
        res = self.set_report_form(
            project,
            form_name=form_name,
            form_synonym=form_synonym,
            fields=fields,
            groups=groups,
            commands=commands,
            events=events,
            spreadsheet_fields=spreadsheet_fields,
        )
        return {"kind": kind, **res}

    def set_dcs(
        self,
        project: str,
        query: str | None = None,
        fields: list | None = None,
        datasets: list | None = None,
        dataset_links: list | None = None,
        parameters: list | None = None,
        calculated_fields: list | None = None,
        totals: list | None = None,
        layout: dict | None = None,
        standard_period: bool = False,
    ) -> dict:
        """Data composition schema, decoupled from "report" naming (DCS attaches to
        Catalog/Document too -- Stage G). Today only report projects carry storage, so a
        processor project is rejected.

        Single dataset: `query` + `fields`. Multi-dataset: `datasets`
        (`[{name, query, fields, data_source?}]`) + `dataset_links` -- mutually exclusive
        with `query`/`fields`. `standard_period=True` prepends the canonical period trio
        (`build_dcs_standard_period_params`) to `parameters` (reference the boundaries as
        `&НачалоПериода`/`&КонецПериода` in the query); it is opt-in, not inferred."""
        kind = self._resolve_kind(project)
        if kind != "report":
            raise ValueError(
                "set_dcs пока поддержан только для отчётов (report); "
                "крепление СКД к Catalog/Document — Stage G"
            )
        if datasets and (query is not None or fields is not None):
            raise ValueError(
                "datasets взаимоисключимо с query/fields (либо один набор query+fields, "
                "либо несколько datasets)"
            )
        if standard_period:
            existing = {p.get("name") for p in (parameters or [])}
            trio = [p for p in build_dcs_standard_period_params() if p["name"] not in existing]
            parameters = trio + list(parameters or [])
        return self.set_report_skd(
            project,
            query=query,
            fields=fields,
            datasets=datasets,
            dataset_links=dataset_links,
            parameters=parameters,
            calculated_fields=calculated_fields,
            totals=totals,
            layout=layout,
        )

    def set_template(
        self, project: str, areas: list, template_name: str | None = None
    ) -> dict:
        """MXL spreadsheet template (`set_report_template`). Reports only -- processors
        have no printed template."""
        kind = self._resolve_kind(project)
        if kind != "report":
            raise ValueError("set_template поддержан только для отчётов (report)")
        return self.set_report_template(project, areas, template_name=template_name)

    def set_module(self, project: str, module: str, code: str) -> dict:
        """Module text: `set_module_code` + `set_report_module_code`."""
        kind = self._resolve_kind(project)
        if kind == "processor":
            return {"kind": kind, **self.set_module_code(project, module, code)}
        return {"kind": kind, **self.set_report_module_code(project, code, module=module)}

    def patch_module(
        self, project: str, module: str, old: str, new: str, replace_all: bool = False
    ) -> dict:
        """Targeted edit of one module (str_replace/Edit semantics), so an agent needn't
        resend a whole ~12k-char module for a two-line change (and can't clobber unrelated
        code by re-pasting). Exact-substring `old` -> `new`; `old` must occur exactly once
        unless `replace_all`. The module must already exist (via `set_module`). Stores
        through the same kind-branching path as `set_module`."""
        if not old:
            raise ValueError("old не может быть пустым")
        if old == new:
            raise ValueError("old и new совпадают — нечего менять")
        kind = self._resolve_kind(project)
        code = (self._get_row(project, kind).get("modules") or {}).get(module)
        if code is None:
            raise ValueError(
                f"модуль «{module}» ещё не задан для «{project}» — сначала создайте его set_module"
            )
        count = code.count(old)
        if count == 0:
            raise ValueError(f"фрагмент не найден в модуле «{module}»")
        if count > 1 and not replace_all:
            raise ValueError(
                f"фрагмент встречается {count} раз(а) в «{module}»; "
                f"уточните old (добавьте контекст) или передайте replace_all=true"
            )
        new_code = code.replace(old, new)
        self.set_module(project, module, new_code)
        return {
            "kind": kind,
            "name": project,
            "module": module,
            "replacements": count if replace_all else 1,
            "code_length": len(new_code),
        }

    def validate(self, project: str, version: str | None = None) -> dict:
        """Library XML + BSL (+ handlers for processors) via one kind-branching helper."""
        kind = self._resolve_kind(project)
        return do_validate(self._get_row(project, kind), kind, self.help_tools, version)

    def export(self, project: str, path: str) -> dict:
        """Build, validate, and write the project tree via one kind-branching helper.
        Result is project-shaped (`kind`, `project`, `project_dir`, ...) for both kinds."""
        kind = self._resolve_kind(project)
        return do_export(self._get_row(project, kind), kind, Path(path))
