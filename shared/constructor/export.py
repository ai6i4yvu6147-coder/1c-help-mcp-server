"""Build, validate, and write external data processor / report file trees.

One module for both object views (was split as ``export.py`` + ``export_report.py``).
``build_trees(project, kind)`` returns role-keyed ``Node`` trees; ``export(project, kind,
parent_dir)`` validates and writes them. The on-disk layout is identical for both kinds:
``parent_dir/<Name>/<Name>.xml`` (root) + ``parent_dir/<Name>/<Name>/...`` (content).

``kind`` is ``'processor'`` | ``'report'``; for a report the archetype (``'skd'``/``'macet'``)
comes from ``project['kind']``. See ``docs/group/handoff-external-report-skd.md`` (SKD) and
``handoff-layout-report.md`` (layout/macet) for the two report archetypes.
"""
from pathlib import Path

from onec_metadata_schema import serialize, validate
from onec_metadata_schema.builder import (
    build_external_data_processor,
    build_external_report,
    build_form_descriptor,
    build_form_layout,
    build_template_descriptor,
)
from onec_metadata_schema.dcs import (
    build_dcs_calculated_field,
    build_dcs_dataset_link,
    build_dcs_flat_layout,
    build_dcs_group_item,
    build_dcs_group_layout,
    build_dcs_parameter,
    build_dcs_query_dataset,
    build_dcs_query_dataset_field,
    build_dcs_schema,
    build_dcs_table_layout,
    build_dcs_total_field,
)
from onec_metadata_schema.spreadsheet import build_spreadsheet_template

DEFAULT_SCHEMA_NAME = "ОсновнаяСхемаКомпоновкиДанных"
DEFAULT_TEMPLATE_NAME = "Макет"

# Common form handler -> platform event name (legacy string events in DB).
_HANDLER_TO_EVENT = {
    "ПриОткрытии": "OnOpen",
    "ПриЗакрытии": "OnClose",
    "ПриСозданииНаСервере": "OnCreateAtServer",
}


def form_events_for_builder(form_events: list | None) -> list[dict] | None:
    """Normalize stored form_events to build_form_layout events=[{event, handler}, ...]."""
    if not form_events:
        return None
    result: list[dict] = []
    for entry in form_events:
        if isinstance(entry, str):
            handler = entry
            event = _HANDLER_TO_EVENT.get(handler)
            if not event:
                raise ValueError(
                    f"событие «{handler}»: укажите {{event, handler}}, "
                    f"например {{event: 'OnOpen', handler: 'ПриОткрытии'}}"
                )
            result.append({"event": event, "handler": handler})
        elif isinstance(entry, dict):
            if entry.get("event") and entry.get("handler"):
                result.append({"event": entry["event"], "handler": entry["handler"]})
            else:
                handler = entry.get("handler") or entry.get("name", "")
                event = entry.get("event") or _HANDLER_TO_EVENT.get(handler, "")
                if not event or not handler:
                    raise ValueError(
                        f"событие {entry!r}: нужны event и handler "
                        f"(например event='OnOpen', handler='ПриОткрытии')"
                    )
                result.append({"event": event, "handler": handler})
    return result or None


# --- DCS (report/skd) input -> library builders --------------------------------------

def _build_dataset_fields(fields: list[dict]) -> list:
    result = []
    for field in fields:
        result.append(
            build_dcs_query_dataset_field(
                field["data_path"],
                title_ru=field.get("title_ru"),
                role=field.get("role"),
                format_string=field.get("format_string"),
            )
        )
    return result


def _build_parameters(parameters: list[dict]) -> list:
    result = []
    for param in parameters:
        result.append(
            build_dcs_parameter(
                param["name"],
                param["value_type"],
                title_ru=param.get("title_ru"),
                qualifiers=param.get("qualifiers"),
                use_restriction=param.get("use_restriction", False),
                expression=param.get("expression"),
                use=param.get("use"),
                value_list_allowed=param.get("value_list_allowed", False),
                default_nil=param.get("default_nil", False),
                default_value=param.get("default_value"),
                default_standard_period=param.get("default_standard_period", False),
            )
        )
    return result


def _build_calculated(calculated: list[dict]) -> list:
    result = []
    for item in calculated:
        result.append(
            build_dcs_calculated_field(
                item["data_path"],
                item["expression"],
                item["value_type"],
                title_ru=item.get("title_ru"),
                qualifiers=item.get("qualifiers"),
                format_string=item.get("format_string"),
            )
        )
    return result


def _build_totals(totals: list[dict]) -> list:
    return [
        build_dcs_total_field(item["data_path"], item["expression"])
        for item in totals
    ]


def _build_datasets(report: dict) -> tuple[list, list]:
    """(datasets, dataset_links) for the schema. Multi-dataset when ``report['datasets']``
    is set (each ``{name, query, fields, data_source?}`` + ``dataset_links``); otherwise a
    single query dataset from the flat ``query_text``/``fields``."""
    datasets_spec = report.get("datasets") or []
    if not datasets_spec:
        single = build_dcs_query_dataset(
            report.get("query_text") or "",
            _build_dataset_fields(report.get("fields") or []),
        )
        return [single], []

    datasets = []
    for ds in datasets_spec:
        kwargs = {}
        if ds.get("name"):
            kwargs["name"] = ds["name"]
        if ds.get("data_source"):
            kwargs["data_source"] = ds["data_source"]
        datasets.append(
            build_dcs_query_dataset(
                ds.get("query") or "",
                _build_dataset_fields(ds.get("fields") or []),
                **kwargs,
            )
        )
    links = [
        build_dcs_dataset_link(
            link["source_dataset"],
            link["destination_dataset"],
            link["source_expression"],
            link["destination_expression"],
            required=link.get("required", True),
        )
        for link in (report.get("dataset_links") or [])
    ]
    return datasets, links


def _normalize_group_item(spec: dict) -> dict:
    if "field" in spec and "group_type" in spec and "nested" not in spec:
        return build_dcs_group_item(spec["field"], group_type=spec.get("group_type", "Items"))
    return spec


def _normalize_rows(rows: list) -> list:
    normalized = []
    for row in rows:
        if isinstance(row, dict) and "nested" in row:
            normalized.append(
                {
                    "field": row["field"],
                    "group_type": row.get("group_type", "Items"),
                    "nested": [_normalize_group_item(n) for n in row["nested"]],
                }
            )
        else:
            normalized.append(_normalize_group_item(row))
    return normalized


def _build_layout(layout: dict):
    """Dispatch to the matching DCS layout archetype builder by `layout['mode']`
    (`group_with_details`, `pivot_table`, `flat`) -- inferred from shape (`group_by` vs
    `rows`/`columns` vs neither) when `mode` is omitted."""
    variant_name = layout.get("variant_name", "Основной")
    selection = layout.get("selection") or []
    filter_items = layout.get("filter_items") or []
    data_parameters = layout.get("data_parameters") or []
    order_items = layout.get("order_items") or []
    output_parameters = layout.get("output_parameters") or []
    conditional_appearance = layout.get("conditional_appearance") or []

    mode = layout.get("mode")
    if mode is None:
        if layout.get("group_by"):
            mode = "group_with_details"
        elif layout.get("rows") or layout.get("columns"):
            mode = "pivot_table"
        else:
            mode = "flat"

    if mode == "group_with_details":
        group_by = [_normalize_group_item(g) for g in (layout.get("group_by") or [])]
        return build_dcs_group_layout(
            group_by=group_by,
            variant_name=variant_name,
            selection=selection,
            filter_items=filter_items,
            data_parameters=data_parameters,
            order_items=order_items,
            output_parameters=output_parameters,
            conditional_appearance=conditional_appearance,
        )
    if mode == "pivot_table":
        return build_dcs_table_layout(
            variant_name=variant_name,
            rows=_normalize_rows(layout.get("rows") or []),
            columns=[_normalize_group_item(c) for c in (layout.get("columns") or [])],
            selection=selection,
            filter_items=filter_items,
            data_parameters=data_parameters,
            order_items=order_items,
            output_parameters=output_parameters,
            conditional_appearance=conditional_appearance,
        )
    if mode == "flat":
        return build_dcs_flat_layout(
            variant_name=variant_name,
            selection=selection,
            filter_items=filter_items,
            data_parameters=data_parameters,
            order_items=order_items,
            output_parameters=output_parameters,
            conditional_appearance=conditional_appearance,
        )
    raise ValueError(
        f"layout.mode {mode!r} не поддерживается "
        f"(ожидается group_with_details, pivot_table или flat)"
    )


# --- Tree builders (role-keyed dicts) ------------------------------------------------

def _build_processor_trees(proc: dict) -> dict:
    name = proc["name"]
    form_name = proc.get("form_name") or "Форма"
    form_synonym = proc.get("form_synonym_ru") or form_name

    object_root = build_external_data_processor(
        name=name,
        synonym_ru=proc["synonym_ru"],
        attributes=proc.get("attributes", []),
        form_name=form_name,
    )
    form_descriptor_root = build_form_descriptor(form_name, form_synonym)
    form_layout_root = build_form_layout(
        object_type_raw=f"cfg:ExternalDataProcessorObject.{name}",
        fields=proc.get("form_fields") or None,
        groups=proc.get("form_groups") or None,
        commands=proc.get("form_commands") or None,
        events=form_events_for_builder(proc.get("form_events")),
    )
    return {
        "object": object_root,
        "form_descriptor": form_descriptor_root,
        "form_layout": form_layout_root,
    }


def _build_skd_trees(report: dict) -> dict:
    name = report["name"]
    schema_name = report.get("schema_name") or DEFAULT_SCHEMA_NAME

    report_root = build_external_report(name, report["synonym_ru"], schema_name=schema_name)
    template_descriptor_root = build_template_descriptor(
        schema_name,
        report.get("schema_synonym_ru") or "Основная схема компоновки данных",
    )

    layout = report.get("layout") or {}
    datasets, dataset_links = _build_datasets(report)
    # DB row stores calculated fields under the key `calculated` (from `calculated_json`);
    # accept `calculated_fields` too for callers passing a raw builder-shaped dict.
    calculated = report.get("calculated")
    if calculated is None:
        calculated = report.get("calculated_fields") or []
    schema_root = build_dcs_schema(
        datasets=datasets,
        dataset_links=dataset_links,
        calculated_fields=_build_calculated(calculated),
        total_fields=_build_totals(report.get("totals") or []),
        parameters=_build_parameters(report.get("parameters") or []),
        settings_variant=_build_layout(layout) if layout else None,
    )
    return {
        "report": report_root,
        "template_descriptor": template_descriptor_root,
        "schema": schema_root,
    }


def _build_layout_trees(report: dict) -> dict:
    name = report["name"]
    form_name = report.get("form_name") or "Форма"
    form_synonym = report.get("form_synonym_ru") or form_name
    template_name = report.get("template_name") or DEFAULT_TEMPLATE_NAME

    report_root = build_external_report(
        name,
        report["synonym_ru"],
        schema_name=None,
        form_name=form_name,
        attributes=report.get("attributes") or [],
        tabular_sections=report.get("tabular_sections") or [],
        extra_templates=[template_name],
    )
    form_descriptor_root = build_form_descriptor(form_name, form_synonym)
    form_layout_root = build_form_layout(
        object_type_raw=f"cfg:ExternalReportObject.{name}",
        fields=report.get("form_fields") or None,
        groups=report.get("form_groups") or None,
        commands=report.get("form_commands") or None,
        events=form_events_for_builder(report.get("form_events")),
        spreadsheet_fields=report.get("form_spreadsheet_fields") or None,
        is_report_form=True,
    )
    template_descriptor_root = build_template_descriptor(
        template_name, template_name, template_type="SpreadsheetDocument"
    )
    macet_root = build_spreadsheet_template(report.get("template_areas") or [])
    return {
        "report": report_root,
        "form_descriptor": form_descriptor_root,
        "form_layout": form_layout_root,
        "template_descriptor": template_descriptor_root,
        "macet": macet_root,
    }


def _report_archetype(report: dict) -> str:
    return "macet" if (report.get("kind") or "skd") == "macet" else "skd"


def build_trees(project: dict, kind: str) -> dict:
    """Role-keyed ``Node`` trees for a project. ``kind``: ``'processor'`` | ``'report'``;
    a report branches to skd or macet by ``project['kind']``."""
    if kind == "processor":
        return _build_processor_trees(project)
    if kind == "report":
        if _report_archetype(project) == "macet":
            return _build_layout_trees(project)
        return _build_skd_trees(project)
    raise ValueError(f"неизвестный kind {kind!r} (ожидается processor или report)")


def validate_trees(roots: dict) -> list[str]:
    """Run library validate() across every role tree."""
    errors: list[str] = []
    for node in roots.values():
        errors.extend(validate(node))
    return errors


# --- File writers --------------------------------------------------------------------

def _write(path: Path, node, parent_dir: Path, written: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize(node), encoding="utf-8")
    written.append(str(path.relative_to(parent_dir)))


def _write_bsl(path: Path, code: str, parent_dir: Path, written: list[str]):
    if not code:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(code, encoding="utf-8")
    written.append(str(path.relative_to(parent_dir)))


def _write_processor(proc, roots, project_dir, content_dir, parent_dir) -> list[str]:
    name = proc["name"]
    form_name = proc.get("form_name") or "Форма"
    modules = proc.get("modules") or {}
    written: list[str] = []

    _write(project_dir / f"{name}.xml", roots["object"], parent_dir, written)
    _write(content_dir / "Forms" / f"{form_name}.xml", roots["form_descriptor"], parent_dir, written)
    _write(content_dir / "Forms" / form_name / "Ext" / "Form.xml", roots["form_layout"], parent_dir, written)
    _write_bsl(content_dir / "Ext" / "ObjectModule.bsl", modules.get("ObjectModule", ""), parent_dir, written)
    _write_bsl(
        content_dir / "Forms" / form_name / "Ext" / "Form" / "Module.bsl",
        modules.get("FormModule", ""), parent_dir, written,
    )
    return written


def _write_skd(report, roots, project_dir, content_dir, parent_dir) -> list[str]:
    name = report["name"]
    schema_name = report.get("schema_name") or DEFAULT_SCHEMA_NAME
    written: list[str] = []

    _write(project_dir / f"{name}.xml", roots["report"], parent_dir, written)
    _write(content_dir / "Templates" / f"{schema_name}.xml", roots["template_descriptor"], parent_dir, written)
    _write(content_dir / "Templates" / schema_name / "Ext" / "Template.xml", roots["schema"], parent_dir, written)
    _write_bsl(
        content_dir / "Ext" / "ObjectModule.bsl",
        (report.get("modules") or {}).get("ObjectModule", ""), parent_dir, written,
    )
    return written


def _write_layout(report, roots, project_dir, content_dir, parent_dir) -> list[str]:
    name = report["name"]
    form_name = report.get("form_name") or "Форма"
    template_name = report.get("template_name") or DEFAULT_TEMPLATE_NAME
    modules = report.get("modules") or {}
    written: list[str] = []

    _write(project_dir / f"{name}.xml", roots["report"], parent_dir, written)
    _write(content_dir / "Forms" / f"{form_name}.xml", roots["form_descriptor"], parent_dir, written)
    _write(content_dir / "Forms" / form_name / "Ext" / "Form.xml", roots["form_layout"], parent_dir, written)
    _write(content_dir / "Templates" / f"{template_name}.xml", roots["template_descriptor"], parent_dir, written)
    _write(content_dir / "Templates" / template_name / "Ext" / "Template.xml", roots["macet"], parent_dir, written)
    _write_bsl(content_dir / "Ext" / "ObjectModule.bsl", modules.get("ObjectModule", ""), parent_dir, written)
    _write_bsl(
        content_dir / "Forms" / form_name / "Ext" / "Form" / "Module.bsl",
        modules.get("FormModule", ""), parent_dir, written,
    )
    return written


def export(project: dict, kind: str, parent_dir: Path) -> dict:
    """Build, validate, and write ``project`` under ``parent_dir/<Name>/``. Raises
    ``ValueError`` on validation errors. Returns a project-shaped result: ``{kind, project,
    parent_dir, project_dir, open_in_configurator, files}`` (files relative to parent_dir)."""
    roots = build_trees(project, kind)
    errors = validate_trees(roots)
    if errors:
        raise ValueError("ошибки validate():\n" + "\n".join(f"  - {e}" for e in errors))

    name = project["name"]
    parent_dir = Path(parent_dir)
    project_dir = parent_dir / name
    content_dir = project_dir / name

    if kind == "processor":
        written = _write_processor(project, roots, project_dir, content_dir, parent_dir)
    elif _report_archetype(project) == "macet":
        written = _write_layout(project, roots, project_dir, content_dir, parent_dir)
    else:
        written = _write_skd(project, roots, project_dir, content_dir, parent_dir)

    return {
        "kind": kind,
        "project": name,
        "parent_dir": str(parent_dir),
        "project_dir": str(project_dir),
        "open_in_configurator": str(project_dir / f"{name}.xml"),
        "files": written,
    }
