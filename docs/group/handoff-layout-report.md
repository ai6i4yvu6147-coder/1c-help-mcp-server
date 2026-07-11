# Handoff: layout ("macet") report — second report archetype

**Naming note:** the DB/API value is `kind='macet'`, not `'layout'` — the SKD side
already overloads "layout" (`set_report_skd`'s `layout` param, `build_dcs_schema`'s
`layout_mode`, for DCS `StructureItemGroup`/`Table` grouping). Reusing that word for
the report archetype too would collide in the same file (`export_report.py` checks both
`report.get("layout")` and `report.get("kind")` in the SKD path). This doc's title/prose
still says "layout report" for readability — only the code-level string is `macet`.

**Date:** 2026-07-11
**Source example:** `ФТ_ОтчетБДР` (real Configurator export, АСБ:Бухгалтерия extension `ФТ_Бюджетирование`) + `ФТ_ОтчетыБюджетСервер` common module (real macet-output code) + `Reports/АнализРаспределенияНДС/Templates/Таблица` (confirmed spreadsheet-document wire format, named areas).

## Status

| Area | State |
|------|-------|
| `1c-metadata-schema`: `build_external_report` extended (attributes/tabular_sections/form_name, `schema_name=None`) | **Done** |
| `1c-metadata-schema`: `build_tabular_section` | **Done** |
| `1c-metadata-schema`: `build_template_descriptor(template_type=...)` | **Done** |
| `1c-metadata-schema`: `onec_metadata_schema.spreadsheet` (`build_spreadsheet_template`) | **Done** — named row-range areas, text/parameter cells, `[Token]` text, colspan merges, bold/align/number-format/border |
| `1c-metadata-schema`: `build_spreadsheet_field` + `build_form_layout(spreadsheet_fields=...)` | **Done** — the only way a macet report's form can display `ТабДок.Вывести(...)` output |
| `1c-metadata-schema`: `build_form_layout(is_report_form=True)` | **Done** — `ReportFormType`/`AutoShowState`/`ReportResultViewMode`/`ViewModeApplicationOnSetReportResult` |
| `1c-metadata-schema`: `build_form_descriptor` — `UsePurposes` | **Done** — unconditional (report + processor forms alike) |
| `1c-metadata-schema`: `ExternalReport` root — `MainDataCompositionSchema`/`VariantsStorage` self-close (not omitted) when `schema_name=None` | **Done** |
| `1c-help-mcp`: `report` DB schema (`kind`, attributes/tabular_sections/form/template columns, `form_spreadsheet_fields_json`) | **Done** |
| `1c-help-mcp`: MCP tools `set_report_attributes`, `set_report_tabular_sections`, `set_report_form` (incl. `spreadsheet_fields`), `set_report_template`, `set_report_module_code(module=FormModule)` | **Done** |
| `1c-help-mcp`: `export_report.py` layout branch (writes `Forms/`, `Templates/<macet>/Ext/Template.xml`, `Ext/ObjectModule.bsl`, `Forms/<form>/Ext/Form/Module.bsl`) | **Done**, verified end-to-end through the real MCP tools (`ТрудозатратыПоИсполнителямМакет`, Задачник project, 2026-07-11) |
| Borders beyond a single thin/solid style, background fills, per-column width catalog, print settings | **Deliberately out of scope** — additive later, not required for a valid Configurator load per the two reference files |

## Why a second archetype

SKD reports (`docs/group/handoff-external-report-skd.md`) cover query + DCS grouping/pivot. Real reports with a hand-designed print layout and a custom UI (filters, multi-select organization/period lists, dynamically shown columns) use a **different, older, still fully current** pattern: no DCS at all, own object requisites, own managed form, and a spreadsheet-document "macet" filled cell-by-cell in BSL.

`ФТ_ОтчетБДР` is real but far more complex than the archetype (dynamic macet variants, catalog-driven block/row structure, formula engine) — its macet-filling logic lives in a *shared common module* (`ФТ_ОтчетыБюджетСервер`, in the base config extension, not in the report export itself). **That split is not the normal pattern** — normal layout reports keep their fill logic in their own `ObjectModule`/`FormModule`. The engine targets the normal pattern; `ФТ_ОтчетыБюджетСервер` only served as a reference for confirming the real 1C macet API (`ПолучитьОбласть`/`Вывести`/`Параметры`/`Присоединить`/`Объединить`/`НачатьАвтогруппировкуСтрок`).

## The archetype

**Object (`<Name>.xml`):** no `MainDataCompositionSchema`. Own `Attribute` children stand in for DCS parameters (period bounds, flags, filter values). Own `TabularSection` children stand in for multi-value parameters (organization list, period list) — each gets the mandatory `LineNumber` standard column automatically. `DefaultForm` points at a **local** form (`ExternalReport.<Name>.Form.<FormName>`), with a matching `<Form>` `ChildObjects` ref — unlike the SKD default, which points at the platform's shared `CommonForm.ФормаОтчета` and never ships a local form.

**Form:** a normal managed form (`build_form_layout` — the same builder already used for external data processors; the wire format is identical). Typically: input fields for the period/flags, a table bound to the tabular section(s), a "Сформировать" command, a spreadsheet-document field bound to a `ТабДок` form attribute.

**Template (`TemplateType: SpreadsheetDocument`):** a cell grid with **named row-range areas** (`Макет.ПолучитьОбласть("Шапка")` etc.). Column/grouping freedom is *not* encoded in the macet — it's plain BSL: as many areas as needed (header, per-level row styles, footer/totals), output in a loop with `ТабДок.Вывести(Область, Уровень)` (`Уровень` drives indent/collapsible row groups via `НачатьАвтогруппировкуСтрок`/`ЗакончитьАвтогруппировкуСтрок`). Cell parameters are either a bare `<parameter>Name</parameter>` (whole-cell value) or a `[Name]` token inside literal text — both filled the same way at runtime: `Область.Параметры.Name = значение`.

**Modules:** `ObjectModule` (`СведенияОВнешнейОбработке`, data-gathering, macet-filling procedures) and `FormModule` (command handlers, calls into the object). Both go through `set_report_module_code(report, code, module='ObjectModule'|'FormModule')`.

## MCP flow

1. `create_report(name, synonym, kind='macet')`
2. `set_report_attributes(report, attributes)` / `set_report_tabular_sections(report, tabular_sections)`
3. `set_report_form(report, form_name?, fields?, groups?, commands?, events?)`
4. `set_report_template(report, areas, template_name?)`
5. `set_report_module_code(report, code, module='ObjectModule')` and again with `module='FormModule'`
6. `validate_report(report)`
7. `export_report(report, path)`

## Lessons from the first real MCP build (2026-07-11, `ТрудозатратыПоИсполнителямМакет`)

Built end-to-end through the real MCP tools against the Задачник project (`RegisterInformation.Трудозатраты`, grouped Исполнитель → Задача, detail rows, running total). Validated and exported clean, but needed hand fixes to actually run — three were engine gaps (now fixed, see Status table above), one is a BSL pattern gotcha this doc must teach:

**BSL gotcha — module-level `Экспорт` variables don't reliably round-trip through `Объект.` from FormModule.** The natural-looking pattern:

```bsl
// ObjectModule
Перем ТабДок Экспорт;
Процедура СформироватьНаСервере() Экспорт
	ТабДок = Новый ТабличныйДокумент;
	... ТабДок.Вывести(...) ...
КонецПроцедуры

// FormModule
&НаСервере
Процедура СформироватьНаСервере()
	Объект.СформироватьНаСервере();
	ТабДок = Объект.ТабДок;  // <- unreliable: report/processor form attributes
	                          //    of object type don't guarantee this sees the
	                          //    same server-side instance state
КонецПроцедуры
```

produced an empty result in practice. The working pattern makes the object method a **function that returns** the table document, and the form reads it via `РеквизитФормыВЗначение` (converts the form's `Объект` attribute into a real object value, calls the method on *that* value, captures the return):

```bsl
// ObjectModule
Функция СформироватьНаСервере() Экспорт
	ТабДок = Новый ТабличныйДокумент;
	... ТабДок.Вывести(...) ...
	Возврат ТабДок;
КонецФункции

// FormModule
&НаСервере
Процедура СформироватьНаСервере()
	ТабДок = РеквизитФормыВЗначение("Объект").СформироватьНаСервере();
КонецПроцедуры
```

Agents building `ObjectModule`/`FormModule` code for a macet report via `set_report_module_code` should use this pattern, not the `Перем ... Экспорт` + `Объект.Поле` one — this is a hand-written-BSL concern, not something the constructor schema/tools encode or validate.

**Three engine fidelity gaps**, found by diffing the Configurator-corrected export against the original — all fixed in `1c-metadata-schema` (see Status table):
1. No form control could display the report result at all (`build_spreadsheet_field` was missing entirely until this build).
2. Report forms need `ReportFormType=Main`/`AutoShowState`/`ReportResultViewMode`/`ViewModeApplicationOnSetReportResult` — absent from `build_form_layout`'s output.
3. `UsePurposes` (client availability) missing from `build_form_descriptor`; `MainDataCompositionSchema`/`VariantsStorage` were omitted instead of self-closed on a DCS-less (`schema_name=None`) `ExternalReport`.

**Operator note — build/deploy sync:** this build's *first* export was missing fixes (2) and (3) above even though the library source already had them and the portable server had just been rebuilt+its `constructor.db` deleted. The portable server's build step apparently doesn't always pick up the very latest `1c-metadata-schema` source; if a report built through the live MCP tools is missing something this doc says should be there, suspect a stale bundled library copy before suspecting the report/BSL, and rebuild again.

## Wire-format notes (confirmed against real exports, not guessed)

- Spreadsheet document root: `<document xmlns="http://v8.1c.ru/8.2/data/spreadsheet">`, no `version` attribute (unlike `MetaDataObject`/`Form`).
- Named areas: `<namedItem xsi:type="NamedItemCells"><name>X</name><area><type>Rows</type><beginRow>N</beginRow><endRow>M</endRow><beginColumn>-1</beginColumn><endColumn>-1</endColumn></area></namedItem>` — row ranges, appended after all `rowsItem`/`merge` content.
- Cells: `<c><i>{col}</i><c><f>{formatIndex}</f>{<parameter>Name</parameter> | <tl><v8:item><v8:lang>ru</v8:lang><v8:content>Text [Token]</v8:content></v8:item></tl>}</c></c>`.
- `<border>N</border>` inside a `<format>` indexes directly into the **same** `<line>` catalog used for the format's font — there is no separate composite `Border` object (confirmed: `ФТ_ОтчетБДР` uses `<border>0</border>` and per-side `<leftBorder>0</leftBorder>` etc. resolving into a 1–2 entry `<line>` list).
- `TabularSection`'s `StandardAttributes/xr:StandardAttribute` (`LineNumber`) is fixed boilerplate, verbatim-identical across independent tabular sections on the same export — not caller-configurable.

## Tier boundaries (unchanged from SKD handoff)

Deep macet styling (background fills, multi-weight borders, per-column width catalog, print settings, pictures) is additive future work — none of it blocks a valid Configurator load for the archetype above.
