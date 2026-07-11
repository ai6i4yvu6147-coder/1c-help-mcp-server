"""Build and write external report file trees (SKD or layout/"macet")."""
from pathlib import Path

from onec_metadata_schema import serialize, validate
from onec_metadata_schema.builder import (
    build_external_report,
    build_form_descriptor,
    build_form_layout,
    build_template_descriptor,
)
from onec_metadata_schema.dcs import (
    build_dcs_calculated_field,
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

from shared.constructor.export import form_events_for_builder

DEFAULT_SCHEMA_NAME = "ОсновнаяСхемаКомпоновкиДанных"
DEFAULT_TEMPLATE_NAME = "Макет"


def _build_dataset_fields(fields: list[dict]) -> list:
    result = []
    for field in fields:
        role = field.get("role")
        result.append(
            build_dcs_query_dataset_field(
                field["data_path"],
                title_ru=field.get("title_ru"),
                role=role,
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
    `rows`/`columns` vs neither) when `mode` is omitted. Was previously hardcoded to
    `build_dcs_table_layout` (pivot only, requires both row and column fields) even for
    plain grouped lists -- the single most common report shape -- confirmed a real gap
    while building a group-with-details report (Исполнитель -> Задача, 2 levels +
    per-level subtotals) that `build_dcs_table_layout` cannot express at all."""
    variant_name = layout.get("variant_name", "Основной")
    selection = layout.get("selection") or []
    filter_items = layout.get("filter_items") or []
    data_parameters = layout.get("data_parameters") or []

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
        )
    if mode == "pivot_table":
        return build_dcs_table_layout(
            variant_name=variant_name,
            rows=_normalize_rows(layout.get("rows") or []),
            columns=[_normalize_group_item(c) for c in (layout.get("columns") or [])],
            selection=selection,
            filter_items=filter_items,
            data_parameters=data_parameters,
        )
    if mode == "flat":
        return build_dcs_flat_layout(
            variant_name=variant_name,
            selection=selection,
            filter_items=filter_items,
            data_parameters=data_parameters,
        )
    raise ValueError(
        f"layout.mode {mode!r} не поддерживается "
        f"(ожидается group_with_details, pivot_table или flat)"
    )


def _build_skd_trees(report: dict) -> dict:
    name = report["name"]
    schema_name = report.get("schema_name") or DEFAULT_SCHEMA_NAME

    report_root = build_external_report(name, report["synonym_ru"], schema_name=schema_name)
    template_descriptor_root = build_template_descriptor(
        schema_name,
        report.get("schema_synonym_ru") or "Основная схема компоновки данных",
    )

    layout = report.get("layout") or {}
    schema_root = build_dcs_schema(
        datasets=[
            build_dcs_query_dataset(
                report.get("query_text") or "",
                _build_dataset_fields(report.get("fields") or []),
            ),
        ],
        calculated_fields=_build_calculated(report.get("calculated_fields") or []),
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


def build_trees(report: dict) -> dict:
    """Build the Node trees for a report, keyed by role. Role set depends on
    `report['kind']` ('skd', the default, or 'macet')."""
    if (report.get("kind") or "skd") == "macet":
        return _build_layout_trees(report)
    return _build_skd_trees(report)


def validate_trees(roots: dict) -> list[str]:
    errors: list[str] = []
    for node in roots.values():
        errors.extend(validate(node))
    return errors


def _export_skd(report: dict, roots: dict, report_dir: Path, content_dir: Path, parent_dir: Path) -> list[str]:
    name = report["name"]
    schema_name = report.get("schema_name") or DEFAULT_SCHEMA_NAME
    written: list[str] = []

    root_xml = report_dir / f"{name}.xml"
    root_xml.parent.mkdir(parents=True, exist_ok=True)
    root_xml.write_text(serialize(roots["report"]), encoding="utf-8")
    written.append(str(root_xml.relative_to(parent_dir)))

    template_desc = content_dir / "Templates" / f"{schema_name}.xml"
    template_desc.parent.mkdir(parents=True, exist_ok=True)
    template_desc.write_text(serialize(roots["template_descriptor"]), encoding="utf-8")
    written.append(str(template_desc.relative_to(parent_dir)))

    template_body = content_dir / "Templates" / schema_name / "Ext" / "Template.xml"
    template_body.parent.mkdir(parents=True, exist_ok=True)
    template_body.write_text(serialize(roots["schema"]), encoding="utf-8")
    written.append(str(template_body.relative_to(parent_dir)))

    object_code = (report.get("modules") or {}).get("ObjectModule", "")
    if object_code:
        obj_mod = content_dir / "Ext" / "ObjectModule.bsl"
        obj_mod.parent.mkdir(parents=True, exist_ok=True)
        obj_mod.write_text(object_code, encoding="utf-8")
        written.append(str(obj_mod.relative_to(parent_dir)))

    return written


def _export_layout(report: dict, roots: dict, report_dir: Path, content_dir: Path, parent_dir: Path) -> list[str]:
    name = report["name"]
    form_name = report.get("form_name") or "Форма"
    template_name = report.get("template_name") or DEFAULT_TEMPLATE_NAME
    written: list[str] = []

    root_xml = report_dir / f"{name}.xml"
    root_xml.parent.mkdir(parents=True, exist_ok=True)
    root_xml.write_text(serialize(roots["report"]), encoding="utf-8")
    written.append(str(root_xml.relative_to(parent_dir)))

    form_desc_path = content_dir / "Forms" / f"{form_name}.xml"
    form_desc_path.parent.mkdir(parents=True, exist_ok=True)
    form_desc_path.write_text(serialize(roots["form_descriptor"]), encoding="utf-8")
    written.append(str(form_desc_path.relative_to(parent_dir)))

    form_layout_path = content_dir / "Forms" / form_name / "Ext" / "Form.xml"
    form_layout_path.parent.mkdir(parents=True, exist_ok=True)
    form_layout_path.write_text(serialize(roots["form_layout"]), encoding="utf-8")
    written.append(str(form_layout_path.relative_to(parent_dir)))

    template_desc = content_dir / "Templates" / f"{template_name}.xml"
    template_desc.parent.mkdir(parents=True, exist_ok=True)
    template_desc.write_text(serialize(roots["template_descriptor"]), encoding="utf-8")
    written.append(str(template_desc.relative_to(parent_dir)))

    macet_path = content_dir / "Templates" / template_name / "Ext" / "Template.xml"
    macet_path.parent.mkdir(parents=True, exist_ok=True)
    macet_path.write_text(serialize(roots["macet"]), encoding="utf-8")
    written.append(str(macet_path.relative_to(parent_dir)))

    modules = report.get("modules") or {}
    object_code = modules.get("ObjectModule", "")
    if object_code:
        obj_mod_path = content_dir / "Ext" / "ObjectModule.bsl"
        obj_mod_path.parent.mkdir(parents=True, exist_ok=True)
        obj_mod_path.write_text(object_code, encoding="utf-8")
        written.append(str(obj_mod_path.relative_to(parent_dir)))

    form_code = modules.get("FormModule", "")
    if form_code:
        form_mod_path = content_dir / "Forms" / form_name / "Ext" / "Form" / "Module.bsl"
        form_mod_path.parent.mkdir(parents=True, exist_ok=True)
        form_mod_path.write_text(form_code, encoding="utf-8")
        written.append(str(form_mod_path.relative_to(parent_dir)))

    return written


def export_report(report: dict, parent_dir: Path) -> dict:
    """Build, validate, and write report under parent_dir/<Name>/. Raises ValueError on
    validation errors. See `docs/group/handoff-external-report-skd.md` (SKD) and
    `docs/group/handoff-layout-report.md` (layout/macet) for the two archetypes."""
    roots = build_trees(report)
    errors = validate_trees(roots)
    if errors:
        raise ValueError("ошибки validate():\n" + "\n".join(f"  - {e}" for e in errors))

    name = report["name"]
    parent_dir = Path(parent_dir)
    report_dir = parent_dir / name
    content_dir = report_dir / name

    if (report.get("kind") or "skd") == "macet":
        written = _export_layout(report, roots, report_dir, content_dir, parent_dir)
    else:
        written = _export_skd(report, roots, report_dir, content_dir, parent_dir)

    return {
        "report": name,
        "parent_dir": str(parent_dir),
        "report_dir": str(report_dir),
        "open_in_configurator": str(report_dir / f"{name}.xml"),
        "files": written,
    }
