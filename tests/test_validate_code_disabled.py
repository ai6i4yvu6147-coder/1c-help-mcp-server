"""The heuristic help-level BSL validator is intentionally disabled.

`HelpTools.validate_code` must return no findings for any input (it is a stub seam for a
future real linter). This guards against an accidental partial-revert that would bring
back the mass `unknown_object` false positives on local variables. When a real linter is
written, replace this test along with the stub.
"""
from server.tools import HelpTools


def test_validate_code_is_disabled_returns_empty():
    tools = HelpTools("nonexistent_dir", None)
    # exactly the shapes that used to produce ~50 false `unknown_object` errors:
    # local var receivers, chained calls, an unknown method on a "known" object.
    code = (
        "ТЗ = Новый ТаблицаЗначений;\n"
        "ТЗ.Добавить();\n"
        "Выборка = Запрос.Выполнить().Выбрать();\n"
        "Пока Выборка.Следующий() Цикл\n"
        "    Объект.НекийРеквизит.ЛюбойМетод();\n"
        "КонецЦикла;\n"
        "Справочники.Х.Создать();\n"  # this WAS a valid catch; disabled now too
    )
    assert tools.validate_code(code) == []
    assert tools.validate_code("", version="8.3.27") == []
