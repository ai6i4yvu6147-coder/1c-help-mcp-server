#!/usr/bin/env python
"""Build Planeta stock-by-warehouse external report via constructor (MCP-equivalent flow)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server.constructor_tools import ConstructorTools
from server.tools import HelpTools

REPORT = "OstatkiPoSkladam"
OUTPUT = Path(__file__).resolve().parents[1] / ".tasks" / "planeta-report"


def main() -> int:
    db_dir = Path(__file__).resolve().parents[1] / "databases"
    ct = ConstructorTools(db_dir / "constructor.db", HelpTools(str(db_dir)))

    try:
        ct.create_report(REPORT, "Остатки товаров по складам (Планета)")
    except ValueError as exc:
        if "уже существует" not in str(exc):
            raise

    query = "\n".join([
        "ВЫБРАТЬ",
        "    Остатки.Склад КАК Склад,",
        "    Остатки.Номенклатура КАК Номенклатура,",
        "    Остатки.ВНаличииОстаток КАК Количество",
        "ИЗ",
        "    РегистрНакопления.ТоварыНаСкладах.Остатки(, ) КАК Остатки",
    ])

    ct.set_report_skd(
        REPORT,
        query=query,
        fields=[
            {"data_path": "Склад", "title_ru": "Склад", "role": "dimension"},
            {"data_path": "Номенклатура", "title_ru": "Номенклатура", "role": "dimension"},
            {"data_path": "Количество", "title_ru": "Количество", "format_string": "ЧЦ=15; ЧДЦ=3"},
        ],
        totals=[{"data_path": "Количество", "expression": "Сумма(Количество)"}],
        layout={
            "selection": ["Количество"],
            "rows": [{"field": "Склад", "group_type": "Items"}],
            "columns": [],
        },
    )

    module = """Функция СведенияОВнешнейОбработке() Экспорт

\tПараметрыРегистрации = ДополнительныеОтчетыИОбработки.СведенияОВнешнейОбработке();
\tПараметрыРегистрации.Вид = ДополнительныеОтчетыИОбработкиКлиентСервер.ВидОбработкиДополнительныйОтчет();
\tПараметрыРегистрации.Наименование = "Остатки товаров по складам (Планета)";
\tПараметрыРегистрации.Версия = "1.0";
\tПараметрыРегистрации.БезопасныйРежим = Ложь;
\tПараметрыРегистрации.Информация = "Суммарное количество номенклатуры в разрезе складов (РегистрНакопления.ТоварыНаСкладах)";

\tКоманда = ПараметрыРегистрации.Команды.Добавить();
\tКоманда.Представление = "Остатки по складам";
\tКоманда.Идентификатор = "ОткрытьФорму";
\tКоманда.Использование = "ОткрытиеФормы";
\tКоманда.ПоказыватьОповещение = Ложь;

\tВозврат ПараметрыРегистрации;

КонецФункции"""

    ct.set_report_module_code(REPORT, module)
    validation = ct.validate_report(REPORT)
    if not validation["ok"]:
        print("validate failed:", validation)
        return 1

    result = ct.export_report(REPORT, str(OUTPUT))
    print("OK:", result["open_in_configurator"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
