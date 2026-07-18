"""Unified constructor surface (write-tools-taxonomy.md).

Exercises the `project`-handle facades on `ConstructorTools` end-to-end against a temp
`constructor.db` and temp export dir: routing by kind, non-applicable-combination
rejections, and equivalence of the new `set_dcs` with the legacy `set_report_skd`.
"""
import sqlite3
from pathlib import Path

import pytest

from server.constructor_tools import ConstructorTools
from shared.constructor import db as constructor_db

# The report table exactly as it shipped before datasets_json/dataset_links_json existed.
_OLD_REPORT_DDL = """
CREATE TABLE report (
    name TEXT PRIMARY KEY,
    synonym_ru TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'skd',
    schema_name TEXT NOT NULL DEFAULT 'ОсновнаяСхемаКомпоновкиДанных',
    query_text TEXT NOT NULL DEFAULT '',
    fields_json TEXT NOT NULL DEFAULT '[]',
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
"""


class _StubHelp:
    """validate() only needs help_tools.validate_code(code, version)."""

    def validate_code(self, code, version=None):
        return []


@pytest.fixture
def ct(tmp_path):
    return ConstructorTools(tmp_path / "constructor.db", _StubHelp())


# --- _resolve_kind ---------------------------------------------------------------------

def test_old_db_gets_new_columns_and_multi_dataset_works(tmp_path):
    # A constructor.db from before the datasets columns existed must self-migrate on open.
    db_path = tmp_path / "old.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_OLD_REPORT_DDL)
    conn.commit()
    conn.close()

    cols_before = {r[1] for r in sqlite3.connect(str(db_path)).execute("PRAGMA table_info(report)")}
    assert "datasets_json" not in cols_before

    # open_db (via ConstructorTools) runs the ALTER guard; multi-dataset must then work.
    ct = ConstructorTools(db_path, _StubHelp())
    ct.create("report", "Мигр", "Миграция")
    res = ct.set_dcs("Мигр", datasets=[
        {"name": "Н1", "query": "ВЫБРАТЬ 1 КАК A", "fields": [{"data_path": "A"}]},
    ])
    assert res["dataset_count"] == 1

    cols_after = {r[1] for r in ct._get_connection().execute("PRAGMA table_info(report)")}
    assert {"datasets_json", "dataset_links_json"} <= cols_after


def test_resolve_kind_processor_and_report(ct):
    ct.create("processor", "Обработка1", "Обработка 1")
    ct.create("report", "Отчет1", "Отчёт 1")
    assert ct._resolve_kind("Обработка1") == "processor"
    assert ct._resolve_kind("Отчет1") == "report"


def test_resolve_kind_missing_raises(ct):
    with pytest.raises(ValueError, match="не найден"):
        ct._resolve_kind("Нет")


def test_resolve_kind_ambiguous_raises(ct):
    # Same name in both tables -> refuse to guess.
    ct.create("processor", "Общий", "Общий")
    ct.create("report", "Общий", "Общий")
    with pytest.raises(ValueError, match="неоднозначно"):
        ct._resolve_kind("Общий")


# --- create ----------------------------------------------------------------------------

def test_create_processor(ct):
    res = ct.create("processor", "Обр", "Обработка")
    assert res["kind"] == "processor"
    assert res["name"] == "Обр"


def test_create_report_default_archetype_skd(ct):
    res = ct.create("report", "Отч", "Отчёт")
    assert res["kind"] == "report"
    assert res["archetype"] == "skd"


def test_create_report_macet_archetype(ct):
    res = ct.create("report", "ОтчМакет", "Отчёт макет", archetype="macet")
    assert res["archetype"] == "macet"


def test_create_processor_rejects_archetype(ct):
    with pytest.raises(ValueError, match="archetype применим только к kind=report"):
        ct.create("processor", "Обр", "Обработка", archetype="skd")


def test_create_unknown_kind_raises(ct):
    with pytest.raises(ValueError, match="kind"):
        ct.create("catalog", "Спр", "Справочник")


# --- set_object ------------------------------------------------------------------------

def test_set_object_processor_attributes(ct):
    ct.create("processor", "Обр", "Обработка")
    res = ct.set_object("Обр", attributes=[{"name": "Орг", "type_raw": "xs:string"}])
    assert res["kind"] == "processor"
    assert len(res["attributes"]) == 1


def test_set_object_processor_rejects_tabular_sections(ct):
    ct.create("processor", "Обр", "Обработка")
    with pytest.raises(ValueError, match="табличные части"):
        ct.set_object("Обр", tabular_sections=[{"name": "ТЧ", "attributes": []}])


def test_set_object_report_attributes_and_tabular_sections(ct):
    ct.create("report", "Отч", "Отчёт", archetype="macet")
    res = ct.set_object(
        "Отч",
        attributes=[{"name": "НачалоПериода", "type_raw": "xs:dateTime"}],
        tabular_sections=[{"name": "Организации", "attributes": [
            {"name": "Организация", "type_raw": "xs:string"},
        ]}],
    )
    assert res["kind"] == "report"
    assert len(res["attributes"]) == 1
    assert len(res["tabular_sections"]) == 1


def test_set_object_requires_something(ct):
    ct.create("report", "Отч", "Отчёт")
    with pytest.raises(ValueError, match="укажите"):
        ct.set_object("Отч")


# --- set_form_any ----------------------------------------------------------------------

def test_set_form_processor(ct):
    ct.create("processor", "Обр", "Обработка")
    res = ct.set_form_any("Обр", fields=[{"name": "Поле", "type_raw": "xs:string"}])
    assert res["kind"] == "processor"
    assert len(res["form_fields"]) == 1


def test_set_form_processor_rejects_report_only_params(ct):
    ct.create("processor", "Обр", "Обработка")
    with pytest.raises(ValueError, match="только fields/groups/commands/events"):
        ct.set_form_any("Обр", spreadsheet_fields=[{"name": "ТабДок"}])


def test_set_form_report_with_spreadsheet_field(ct):
    ct.create("report", "Отч", "Отчёт", archetype="macet")
    res = ct.set_form_any(
        "Отч",
        form_name="ФормаОтчета",
        fields=[{"name": "Поле", "type_raw": "xs:string"}],
        spreadsheet_fields=[{"name": "ТабДок"}],
    )
    assert res["kind"] == "report"
    assert res["form_name"] == "ФормаОтчета"
    assert len(res["form_spreadsheet_fields"]) == 1


# --- set_dcs ---------------------------------------------------------------------------

def _skd_inputs():
    return dict(
        query="ВЫБРАТЬ 1 КАК Сумма, 2 КАК Организация",
        fields=[{"data_path": "Сумма"}, {"data_path": "Организация"}],
        totals=[{"data_path": "Сумма", "expression": "Сумма(Сумма)"}],
        layout={"mode": "group_with_details", "group_by": [{"field": "Организация"}],
                "selection": ["Сумма"]},
    )


def test_set_dcs_report(ct):
    ct.create("report", "Отч", "Отчёт")
    res = ct.set_dcs("Отч", **_skd_inputs())
    assert res["field_count"] == 2
    assert res["has_layout"] is True


def test_set_dcs_processor_rejected(ct):
    ct.create("processor", "Обр", "Обработка")
    with pytest.raises(ValueError, match="только для отчётов"):
        ct.set_dcs("Обр", **_skd_inputs())


def test_set_dcs_layout_order_items_reach_schema(ct, tmp_path):
    # order_items in layout must flow through set_dcs -> _build_layout -> dcsset:order.
    ct.create("report", "СОтч", "Отчёт с сортировкой")
    inputs = _skd_inputs()
    inputs["layout"]["order_items"] = [{"field": "Организация", "direction": "Desc"}]
    ct.set_dcs("СОтч", **inputs)
    ct.export("СОтч", str(tmp_path / "out"))
    schema = (tmp_path / "out" / "СОтч" / "СОтч" / "Templates"
              / "ОсновнаяСхемаКомпоновкиДанных" / "Ext" / "Template.xml").read_text(encoding="utf-8")
    assert 'xsi:type="dcsset:OrderItemField"' in schema
    assert "<dcsset:orderType>Desc</dcsset:orderType>" in schema


def _schema_xml(root, name):
    return (root / name / name / "Templates" / "ОсновнаяСхемаКомпоновкиДанных"
            / "Ext" / "Template.xml").read_text(encoding="utf-8")


def test_set_dcs_calculated_field_reaches_schema(ct, tmp_path):
    # Regression: calculated fields are stored under the DB key `calculated`; export must
    # read that key (not `calculated_fields`), else the calc field is silently dropped and
    # any selection/total referencing it dangles.
    ct.create("report", "Вычисл", "С вычисляемым полем")
    ct.set_dcs(
        "Вычисл",
        query="ВЫБРАТЬ 1 КАК Приход, 2 КАК Расход",
        fields=[{"data_path": "Приход"}, {"data_path": "Расход"}],
        calculated_fields=[{
            "data_path": "Оборот", "expression": "Приход - Расход",
            "value_type": "xs:decimal", "title_ru": "Оборот",
        }],
        totals=[{"data_path": "Оборот", "expression": "Сумма(Оборот)"}],
        layout={"mode": "flat", "selection": ["Приход", "Расход", "Оборот"]},
    )
    assert ct.validate("Вычисл")["ok"] is True
    ct.export("Вычисл", str(tmp_path / "out"))
    schema = _schema_xml(tmp_path / "out", "Вычисл")
    assert "<calculatedField>" in schema
    assert "<dataPath>Оборот</dataPath>" in schema


def test_set_dcs_multi_dataset(ct, tmp_path):
    # Register-plus-balance shape: two datasets joined by a dataset link.
    ct.create("report", "Мульти", "Мульти-набор")
    res = ct.set_dcs(
        "Мульти",
        datasets=[
            {"name": "НаборДанных1", "query": "ВЫБРАТЬ 1 КАК Товар, 2 КАК Регистратор",
             "fields": [{"data_path": "Товар", "role": "dimension"}, {"data_path": "Регистратор"}]},
            {"name": "НаборДанных2", "query": "ВЫБРАТЬ 1 КАК Товар, 0 КАК Остаток",
             "fields": [{"data_path": "Товар", "role": "dimension"}, {"data_path": "Остаток"}]},
        ],
        dataset_links=[
            {"source_dataset": "НаборДанных1", "destination_dataset": "НаборДанных2",
             "source_expression": "Товар", "destination_expression": "Товар"},
        ],
    )
    assert res["dataset_count"] == 2
    assert res["field_count"] == 4
    assert ct.validate("Мульти")["ok"] is True

    ct.export("Мульти", str(tmp_path / "out"))
    schema = _schema_xml(tmp_path / "out", "Мульти")
    assert schema.count('xsi:type="DataSetQuery"') == 2
    assert "<dataSetLink>" in schema
    assert "<sourceDataSet>НаборДанных1</sourceDataSet>" in schema


def test_set_dcs_datasets_mutually_exclusive_with_query(ct):
    ct.create("report", "Мульти2", "М2")
    with pytest.raises(ValueError, match="взаимоисключимо"):
        ct.set_dcs(
            "Мульти2",
            query="ВЫБРАТЬ 1 КАК A",
            fields=[{"data_path": "A"}],
            datasets=[{"name": "Н1", "query": "ВЫБРАТЬ 1 КАК A", "fields": [{"data_path": "A"}]}],
        )


def test_set_dcs_datasets_require_valid_names(ct):
    ct.create("report", "Мульти3", "М3")
    with pytest.raises(ValueError, match="набор данных"):
        ct.set_dcs("Мульти3", datasets=[{"query": "ВЫБРАТЬ 1 КАК A", "fields": [{"data_path": "A"}]}])


def test_set_dcs_standard_period_injects_trio(ct, tmp_path):
    ct.create("report", "Период", "Отчёт с периодом")
    ct.set_dcs("Период", query="ВЫБРАТЬ 1 КАК X", fields=[{"data_path": "X"}], standard_period=True)
    ct.export("Период", str(tmp_path / "out"))
    schema = _schema_xml(tmp_path / "out", "Период")
    assert "<name>Период</name>" in schema
    assert "<name>НачалоПериода</name>" in schema
    assert "<name>КонецПериода</name>" in schema
    assert "&amp;Период.ДатаНачала" in schema  # derived-parameter expression


def test_set_dcs_standard_period_dedups_existing_period(ct, tmp_path):
    ct.create("report", "Период2", "П2")
    ct.set_dcs(
        "Период2",
        query="ВЫБРАТЬ 1 КАК X",
        fields=[{"data_path": "X"}],
        parameters=[{"name": "Период", "value_type": "v8:StandardPeriod", "title_ru": "Свой период"}],
        standard_period=True,
    )
    ct.export("Период2", str(tmp_path / "out"))
    schema = _schema_xml(tmp_path / "out", "Период2")
    assert schema.count("<name>Период</name>") == 1  # agent's Период kept, trio's skipped
    assert "Свой период" in schema  # the agent's definition, not the trio's


def test_set_dcs_export_equals_typed_set_report_skd(ct, tmp_path):
    # set_dcs delegates to the typed set_report_skd; identical inputs -> identical export.
    ct.create("report", "Новый", "Новый")
    ct.create("report", "Старый", "Старый")
    ct.set_dcs("Новый", **_skd_inputs())
    ct.set_report_skd("Старый", **_skd_inputs())

    new_dir = tmp_path / "new_export"
    old_dir = tmp_path / "old_export"
    ct.export("Новый", str(new_dir))
    ct.export("Старый", str(old_dir))

    def _schema(root, name):
        return (root / name / name / "Templates"
                / "ОсновнаяСхемаКомпоновкиДанных" / "Ext" / "Template.xml").read_text(encoding="utf-8")

    assert _schema(new_dir, "Новый") == _schema(old_dir, "Старый")


# --- set_template ----------------------------------------------------------------------

def test_set_template_report(ct):
    ct.create("report", "Отч", "Отчёт", archetype="macet")
    res = ct.set_template("Отч", areas=[{"name": "Шапка", "rows": [[{"col": 0, "text": "X"}]]}])
    assert res["area_count"] == 1


def test_set_template_processor_rejected(ct):
    ct.create("processor", "Обр", "Обработка")
    with pytest.raises(ValueError, match="только для отчётов"):
        ct.set_template("Обр", areas=[{"name": "Шапка", "rows": [[{"col": 0, "text": "X"}]]}])


# --- set_module ------------------------------------------------------------------------

def test_set_module_processor_and_report(ct):
    ct.create("processor", "Обр", "Обработка")
    ct.create("report", "Отч", "Отчёт")
    r1 = ct.set_module("Обр", "ObjectModule", "// код")
    r2 = ct.set_module("Отч", "ObjectModule", "// код отчёта")
    assert r1["kind"] == "processor" and r1["module"] == "ObjectModule"
    assert r2["kind"] == "report" and r2["code_length"] == len("// код отчёта")


# --- validate --------------------------------------------------------------------------

def test_validate_processor_and_report(ct):
    ct.create("processor", "Обр", "Обработка")
    ct.set_object("Обр", attributes=[{"name": "Орг", "type_raw": "xs:string"}])
    ct.create("report", "Отч", "Отчёт")
    ct.set_dcs("Отч", **_skd_inputs())
    assert ct.validate("Обр")["ok"] is True
    assert ct.validate("Отч")["ok"] is True


# --- export ----------------------------------------------------------------------------

def test_export_processor_writes_tree(ct, tmp_path):
    ct.create("processor", "Обр", "Обработка")
    ct.set_object("Обр", attributes=[{"name": "Орг", "type_raw": "xs:string"}])
    res = ct.export("Обр", str(tmp_path / "out"))
    assert res["kind"] == "processor"
    assert res["project"] == "Обр"
    assert Path(res["open_in_configurator"]).exists()


def test_export_report_writes_tree(ct, tmp_path):
    ct.create("report", "Отч", "Отчёт")
    ct.set_dcs("Отч", **_skd_inputs())
    res = ct.export("Отч", str(tmp_path / "out"))
    assert res["kind"] == "report"
    assert res["project"] == "Отч"
    assert Path(res["open_in_configurator"]).exists()
