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


def test_e2e_processor_headless_attribute_and_command(dispatch, tmp_path):
    """The three things the constructor was (wrongly) reported as unable to do: a
    headless form requisite (kind='attribute'), a button wired to a command handler, and
    an object module of arbitrary procedures -- through the full dispatch -> export."""
    dispatch("create", {"kind": "processor", "name": "E2EОбрПолн", "synonym": "E2E полная"})
    dispatch("set_object", {
        "project": "E2EОбрПолн",
        "attributes": [{"name": "Комментарий", "type_raw": "xs:string"}],
    })
    dispatch("set_form", {
        "project": "E2EОбрПолн",
        "fields": [
            {"name": "Организация", "type_raw": "cfg:CatalogRef.Организации"},
            {"name": "СлужебныйФлаг", "kind": "attribute", "type_raw": "xs:boolean"},
        ],
        "commands": [{"name": "Заполнить", "title_ru": "Заполнить", "action": "Заполнить"}],
    })
    dispatch("set_module", {
        "project": "E2EОбрПолн", "module": "ObjectModule",
        "code": "Процедура ОбработатьДанные() Экспорт\nКонецПроцедуры",
    })
    dispatch("set_module", {
        "project": "E2EОбрПолн", "module": "FormModule",
        "code": "&НаКлиенте\nПроцедура Заполнить(Команда)\nКонецПроцедуры",
    })

    assert "прошёл проверку" in dispatch("validate", {"project": "E2EОбрПолн"})

    dispatch("export", {"project": "E2EОбрПолн", "path": str(tmp_path / "out")})
    form_xml = (tmp_path / "out" / "E2EОбрПолн" / "E2EОбрПолн"
                / "Forms" / "Форма" / "Ext" / "Form.xml").read_text(encoding="utf-8")
    # A normal field appears twice (control + Attribute); a headless one only as the
    # Attribute -> exactly once. This is the structural proof of "no control emitted".
    assert form_xml.count('name="Организация"') == 2
    assert form_xml.count('name="СлужебныйФлаг"') == 1
    # the command button is present
    assert "ФормаЗаполнить" in form_xml

    obj_module = (tmp_path / "out" / "E2EОбрПолн" / "E2EОбрПолн"
                  / "Ext" / "ObjectModule.bsl").read_text(encoding="utf-8")
    assert "ОбработатьДанные" in obj_module


def test_e2e_processor_form_with_value_table_validates_and_exports(dispatch, tmp_path):
    """Regression: a form with a table+attribute group (таблица значений на форме) used
    to fail validate/export with an opaque `Ошибка: 'column'` while set_form itself
    succeeded. The natural payload (`name` on the table field, no `title_ru`) must now
    round-trip create -> set_form -> validate -> export."""
    dispatch("create", {"kind": "processor", "name": "E2EТабл", "synonym": "E2E таблица"})
    ok = dispatch("set_form", {
        "project": "E2EТабл",
        "fields": [{"name": "Поле1", "type_raw": "xs:string"}],
        "groups": [{
            "name": "Группа1",
            "table": {"name": "Таб1", "data_path": "Атр1", "fields": [{"name": "Кол1"}]},
            "attribute": {"name": "Атр1", "columns": [{"name": "Кол1", "type_raw": "xs:string"}]},
        }],
        "commands": [{"name": "Команда1"}],
    })
    assert "обновлена" in ok  # set_form was fine before too; assert it still is

    # the step that used to raise `'column'`
    assert "прошёл проверку" in dispatch("validate", {"project": "E2EТабл"})

    dispatch("export", {"project": "E2EТабл", "path": str(tmp_path / "out")})
    form_xml = (tmp_path / "out" / "E2EТабл" / "E2EТабл"
                / "Forms" / "Форма" / "Ext" / "Form.xml").read_text(encoding="utf-8")
    assert 'name="Таб1"' in form_xml          # the Table control
    assert 'Атр1.Кол1' in form_xml            # column field bound to <data_path>.<column>


def test_e2e_patch_module_targeted_edit_preserves_surrounding_code(dispatch, tmp_path):
    """patch_module replaces only the targeted fragment; the unrelated procedure stays
    intact -- the "don't clobber the rest of the module on a small edit" guarantee."""
    dispatch("create", {"kind": "processor", "name": "E2EПатч", "synonym": "E2E патч"})
    original = (
        "Процедура Первая()\n"
        "    Значение = 1;\n"
        "КонецПроцедуры\n\n"
        "Процедура Вторая()\n"
        "    Значение = 2;\n"
        "КонецПроцедуры"
    )
    dispatch("set_module", {"project": "E2EПатч", "module": "ObjectModule", "code": original})

    out = dispatch("patch_module", {
        "project": "E2EПатч", "module": "ObjectModule",
        "old": "    Значение = 1;", "new": "    Значение = 42;",
    })
    assert "пропатчен" in out

    dispatch("export", {"project": "E2EПатч", "path": str(tmp_path / "out")})
    code = (tmp_path / "out" / "E2EПатч" / "E2EПатч"
            / "Ext" / "ObjectModule.bsl").read_text(encoding="utf-8")
    assert "Значение = 42;" in code          # target changed
    assert "Значение = 1;" not in code       # old gone
    assert "Процедура Вторая()" in code      # unrelated procedure preserved
    assert "Значение = 2;" in code           # ...and its body untouched


def test_e2e_patch_module_ambiguous_match_rejected_unless_replace_all(dispatch):
    dispatch("create", {"kind": "processor", "name": "E2EПатч2", "synonym": "E2E патч2"})
    dispatch("set_module", {
        "project": "E2EПатч2", "module": "FormModule", "code": "А = 1;\nА = 1;",
    })
    # two matches, no replace_all -> refuse rather than guess
    with pytest.raises(ValueError, match="встречается"):
        dispatch("patch_module", {
            "project": "E2EПатч2", "module": "FormModule", "old": "А = 1;", "new": "А = 2;",
        })
    # explicit replace_all -> both replaced
    out = dispatch("patch_module", {
        "project": "E2EПатч2", "module": "FormModule",
        "old": "А = 1;", "new": "А = 2;", "replace_all": True,
    })
    assert "2 замен" in out


def test_e2e_patch_module_missing_fragment_is_error(dispatch):
    dispatch("create", {"kind": "processor", "name": "E2EПатч3", "synonym": "E2E патч3"})
    dispatch("set_module", {"project": "E2EПатч3", "module": "ObjectModule", "code": "А = 1;"})
    with pytest.raises(ValueError, match="не найден"):
        dispatch("patch_module", {
            "project": "E2EПатч3", "module": "ObjectModule", "old": "Б = 2;", "new": "Б = 3;",
        })


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
