"""End-to-end constructor lifecycle through the real MCP `_dispatch` entrypoint.

Drives the full build with only the unified tools (the agent-facing path), against a
temp `constructor.db` swapped into the server module. Proves create -> set_* -> validate
-> export produces a validated, on-disk file tree — no legacy tools involved.
"""
import asyncio

import pytest

import server.server as s
from server.constructor_tools import ConstructorTools


class _StubHelp:
    def validate_code(self, code, version=None):
        return []


@pytest.fixture
def dispatch(tmp_path, monkeypatch):
    ct = ConstructorTools(tmp_path / "constructor.db", _StubHelp())
    monkeypatch.setattr(s, "constructor_tools", ct)

    def run(name, args):
        return asyncio.run(s._dispatch(name, args))[0].text

    return run


def test_e2e_processor_lifecycle(dispatch, tmp_path):
    assert "Создана обработка" in dispatch(
        "create", {"kind": "processor", "name": "E2EОбр", "synonym": "E2E обработка"}
    )
    dispatch("set_object", {
        "project": "E2EОбр",
        "attributes": [{"name": "Орг", "type_raw": "cfg:CatalogRef.Организации"}],
    })
    dispatch("set_form", {
        "project": "E2EОбр",
        "fields": [{"name": "Орг", "type_raw": "cfg:CatalogRef.Организации"}],
        "events": [{"event": "OnOpen", "handler": "ПриОткрытии"}],
    })
    dispatch("set_module", {
        "project": "E2EОбр",
        "module": "FormModule",
        "code": "&НаСервере\nПроцедура ПриОткрытии(Отказ)\nКонецПроцедуры",
    })

    # validate must pass: library XML ok, BSL stubbed ok, and the OnOpen handler exists.
    assert "прошёл проверку" in dispatch("validate", {"project": "E2EОбр"})

    export_text = dispatch("export", {"project": "E2EОбр", "path": str(tmp_path / "out")})
    assert "E2EОбр" in export_text

    root_xml = tmp_path / "out" / "E2EОбр" / "E2EОбр.xml"
    assert root_xml.exists()
    assert "ExternalDataProcessor" in root_xml.read_text(encoding="utf-8")

    form_xml = tmp_path / "out" / "E2EОбр" / "E2EОбр" / "Forms" / "Форма" / "Ext" / "Form.xml"
    assert form_xml.exists()

    form_module = (tmp_path / "out" / "E2EОбр" / "E2EОбр" / "Forms" / "Форма"
                   / "Ext" / "Form" / "Module.bsl")
    assert form_module.exists()
    assert "ПриОткрытии" in form_module.read_text(encoding="utf-8")


def test_e2e_processor_missing_handler_fails_validate(dispatch):
    """The declared OnOpen handler has no procedure -> validate reports it (not ok)."""
    dispatch("create", {"kind": "processor", "name": "E2EПлохая", "synonym": "E2E плохая"})
    dispatch("set_form", {
        "project": "E2EПлохая",
        "events": [{"event": "OnOpen", "handler": "ПриОткрытии"}],
    })
    text = dispatch("validate", {"project": "E2EПлохая"})
    assert "не прошёл проверку" in text
    assert "ПриОткрытии" in text


def test_e2e_report_skd_lifecycle(dispatch, tmp_path):
    assert "Создан отчёт" in dispatch(
        "create", {"kind": "report", "name": "E2EОтч", "synonym": "E2E отчёт"}
    )
    dispatch("set_dcs", {
        "project": "E2EОтч",
        "query": "ВЫБРАТЬ 1 КАК Сумма, 2 КАК Орг",
        "fields": [{"data_path": "Сумма"}, {"data_path": "Орг"}],
        "totals": [{"data_path": "Сумма", "expression": "Сумма(Сумма)"}],
        "layout": {
            "mode": "group_with_details",
            "group_by": [{"field": "Орг"}],
            "selection": ["Сумма"],
        },
    })
    dispatch("set_module", {
        "project": "E2EОтч",
        "module": "ObjectModule",
        "code": "Функция СведенияОВнешнейОбработке() Экспорт\nКонецФункции",
    })
    assert "прошёл проверку" in dispatch("validate", {"project": "E2EОтч"})

    dispatch("export", {"project": "E2EОтч", "path": str(tmp_path / "out")})
    schema = (tmp_path / "out" / "E2EОтч" / "E2EОтч" / "Templates"
              / "ОсновнаяСхемаКомпоновкиДанных" / "Ext" / "Template.xml")
    assert schema.exists()
    body = schema.read_text(encoding="utf-8")
    assert "DataCompositionSchema" in body
    assert "dcsset:StructureItemGroup" in body


def test_e2e_report_multi_dataset_and_standard_period(dispatch, tmp_path):
    # New set_dcs args (datasets/dataset_links/standard_period) must flow through dispatch.
    dispatch("create", {"kind": "report", "name": "E2EМульти", "synonym": "E2E мульти"})
    text = dispatch("set_dcs", {
        "project": "E2EМульти",
        "standard_period": True,
        "datasets": [
            {"name": "НаборДанных1", "query": "ВЫБРАТЬ 1 КАК Товар, 2 КАК Рег",
             "fields": [{"data_path": "Товар", "role": "dimension"}, {"data_path": "Рег"}]},
            {"name": "НаборДанных2", "query": "ВЫБРАТЬ 1 КАК Товар, 0 КАК Остаток",
             "fields": [{"data_path": "Товар", "role": "dimension"}, {"data_path": "Остаток"}]},
        ],
        "dataset_links": [
            {"source_dataset": "НаборДанных1", "destination_dataset": "НаборДанных2",
             "source_expression": "Товар", "destination_expression": "Товар"},
        ],
    })
    assert "2 набор" in text  # dataset_count reported in the summary
    assert "прошёл проверку" in dispatch("validate", {"project": "E2EМульти"})

    dispatch("export", {"project": "E2EМульти", "path": str(tmp_path / "out")})
    schema = (tmp_path / "out" / "E2EМульти" / "E2EМульти" / "Templates"
              / "ОсновнаяСхемаКомпоновкиДанных" / "Ext" / "Template.xml").read_text(encoding="utf-8")
    assert schema.count('xsi:type="DataSetQuery"') == 2
    assert "<dataSetLink>" in schema
    assert "<name>НачалоПериода</name>" in schema  # standard_period trio injected


def test_e2e_unknown_project_is_error(dispatch):
    # _dispatch wraps errors, but the facade raises on an unknown project.
    with pytest.raises(ValueError, match="не найден"):
        asyncio.run(s._dispatch("set_object", {"project": "Нет", "attributes": []}))
