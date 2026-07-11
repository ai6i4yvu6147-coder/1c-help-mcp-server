# Handoff: external report + SKD (`1c-metadata-schema` ↔ `1c-help-mcp`)

**Date:** 2026-07-11 (updated after MCP E2E)  
**Library slice:** external report shell + semantic DCS builder API + layout archetypes  
**Help-mcp slice:** report constructor MCP tools (Stage E+)

## Status

| Area | State |
|------|--------|
| `1c-metadata-schema` builders + Configurator load | **Done** (RvpDemo, layout archetypes, period preset) |
| `1c-help-mcp` MCP tools | **Done** — `create_report`, `set_report_skd`, `set_report_module_code`, `validate_report`, `export_report` |
| MCP E2E (Planeta reports) | **Done** — full flow via connected MCP after server rebuild |
| `layout_mode` in help-mcp export | **Done** (2026-07-11) — `set_report_skd`'s `layout` now dispatches on `layout.mode` (`group_with_details`/`pivot_table`/`flat`, inferred from shape when omitted) to the matching `build_dcs_*_layout`, not always `build_dcs_table_layout`. Found blocking while building `ТрудозатратыПоИсполнителям` (Задачник project) — a plain grouped-list report couldn't be expressed at all before this fix. |
| `default_standard_period` passthrough in `set_report_skd` parameters | **Done** (2026-07-11) |
| Agent SKD hints doc | **Pending** — `docs/skd-constructor-hints.md` |

Canonical library handoff (API detail): `1c-metadata-schema/docs/group/handoff-external-report-skd.md`.

## Three-file export layout

```
<Name>.xml
<Name>/Templates/<SchemaName>.xml
<Name>/Templates/<SchemaName>/Ext/Template.xml
```

## Library API (summary)

Agents call `build_dcs_*` — **not** raw DCS XML.

| Function | Purpose |
|----------|---------|
| `build_external_report` / `build_template_descriptor` | Report shell + template wrapper |
| `build_dcs_schema(..., layout_mode=..., layout=...)` | Prefer archetype over raw `settings_variant` |
| `build_dcs_query_dataset` + `build_dcs_query_dataset_field` | Query dataset; fields explicit (no virtual-table auto-expand) |
| `build_dcs_standard_period_params()` | `Период` + `НачалоПериода` + `КонецПериода` (reference: `обр РВП`) |
| `build_dcs_group_layout` | Grouped list **with detail rows** → `StructureItemGroup` (reference: corrected `TransformKorrektPlaneta`) |
| `build_dcs_table_layout` | **Pivot only** → `StructureItemTable`; requires `rows` **and** `columns` (reference: `обр РВП`) |
| `build_dcs_flat_layout` | Flat list, no structure item |

### Layout archetypes

| `layout_mode` | When |
|---------------|------|
| `group_with_details` | One-axis grouping + detail rows (e.g. corrections by `Организация`) |
| `pivot_table` | Row and column grouping (e.g. `Период` in columns, `Поставщик` in rows) |
| `flat` | No grouping |

### Period (canonical — do not put `&Период.ДатаНачала` in query text)

- UI parameter: `Период` (`v8:StandardPeriod`, `use: Always`)
- Query parameters: `&НачалоПериода`, `&КонецПериода`
- Derived: `useRestriction: true`, `expression: &Период.ДатаНачала` / `&Период.ДатаОкончания`

Use `build_dcs_standard_period_params()` or equivalent three-parameter spec in `set_report_skd`.

## Lessons from MCP E2E (2026-07-11)

Two layout mistakes when agent copied `обр РВП` blindly:

1. **`StructureItemTable` without columns** — table is for pivot (row + column). Single-axis list → `group_with_details`, not table.
2. **No detail level** — grouped table/group without nested empty `StructureItemGroup` shows only group headers; detail fields need inner group with `SelectedItemAuto`.

**Reference exports:**

| Archetype | File |
|-----------|------|
| `group_with_details` | `TransformKorrektPlaneta` (user-corrected export under `fullAI/`) |
| `pivot_table` | `обр РВП` |

## help-mcp constructor (implemented)

**DB:** `report` + `report_module` in `constructor.db`  
**Code:** `shared/constructor/export_report.py`, `validate_report.py`, `server/constructor_tools.py`

**MCP flow:**

1. `create_report(name, synonym)`
2. `set_report_skd(report, query, fields, parameters, totals?, layout?)` — `layout.mode` picks the archetype (`group_with_details`/`pivot_table`/`flat`)
3. `set_report_module_code(report, code)` — `СведенияОВнешнейОбработке()`, `ДополнительныйОтчет`
4. `validate_report(report)`
5. `export_report(report, path)`

**E2E examples built via MCP:** `OstatkiPoSkladam` (register balances), `TransformKorrektPlaneta` (transformation corrections), `ТрудозатратыПоИсполнителям` (Задачник project — `group_with_details` with **two** `group_by` fields: `Исполнитель` then `Задача`, confirming multi-field `group_by` renders as nested grouping levels with a subtotal at each, not a single composite-key group).

`layout` shape for `group_with_details`, as actually used: `{"mode": "group_with_details", "group_by": [{"field": "Исполнитель"}, {"field": "Задача"}], "selection": [...]}` — `mode` is optional (inferred from `group_by` vs `rows`/`columns` presence).

## Pending in help-mcp

1. **`docs/skd-constructor-hints.md`** — short agent doc: period, archetype picker, query vs SKD grouping.
2. **Demo script** `scripts/build_transform_korrekt_demo.py` — mirror library script, Configurator check.

## Configurator fixes (library, 2026-07-11)

- Duplicate `xmlns:dcscom` on root — `normalize_dcs_serialized_xml()` in `dcs.py`.
- XDTO `valueType` / `Type` — DCS uses direct `v8:Type` child, not MDClasses `<Type>` wrapper.

## Demo scripts (library)

```powershell
python scripts/build_external_report_demo.py .tasks/rvp-demo
python scripts/build_transform_korrekt_demo.py .tasks/transform-korrekt-demo
```

## Tier boundaries (unchanged)

| Tier | Deferred |
|------|----------|
| Tier 2 layout | Deep nesting; charts; multiple variants |
| Reader | Full round-trip on arbitrary real `Template.xml` |
| `1c-config-mcp` | `ExternalReport` as fourth project-root kind |
