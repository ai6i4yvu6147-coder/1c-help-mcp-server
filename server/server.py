"""MCP server for 1C syntax help."""
import asyncio
import json
import sys
import time
from pathlib import Path
from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio

sys.path.insert(0, str(Path(__file__).parent.parent))

from server.tools import HelpTools
from server.constructor_tools import ConstructorTools
from onec_metadata_schema import vocabulary as dcs_vocabulary
from shared.security import mask_secrets
from shared.tool_calls_log import (
    ToolCallLogger,
    inject_correlation_properties,
    tool_calls_db_path,
    utc_now_iso,
)

if getattr(sys, "frozen", False):
    application_path = Path(sys.executable).parent
    project_root = application_path.parent
else:
    application_path = Path(__file__).parent
    project_root = application_path.parent

config_path = project_root / "config.json"
config = {}
if config_path.exists():
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

databases_dir = Path(config.get("databases_dir", "databases"))
if not databases_dir.is_absolute():
    databases_dir = project_root / databases_dir
default_version = config.get("default_version")

tools = HelpTools(str(databases_dir), default_version)
constructor_db_path = databases_dir / "constructor.db"
constructor_tools = ConstructorTools(constructor_db_path, tools)
app = Server("1c-help-server")

# Журнал вызовов инструментов (protocol v1.0.7 §3): <logsDir>/tool-calls.db
_call_logger = ToolCallLogger(tool_calls_db_path(project_root / "logs"))


@app.list_tools()
async def list_tools() -> list[Tool]:
    return inject_correlation_properties([
        Tool(
            name="get_syntax",
            description="Справка по встроенному языку 1С (BSL): метод, свойство, тип, конструкция, глобальная функция. "
                        "Не для языка запросов — для запросов используйте get_query_syntax. "
                        "Параметр name: например 'Запрос.Выполнить', 'Сообщить', 'Если', 'Строка'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Имя: Object.Method, тип, конструкция, функция"},
                    "version": {"type": "string", "description": "Версия платформы (8.3.27), опционально"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="search_syntax",
            description="Полнотекстовый поиск по встроенному языку 1С (BSL). "
                        "Не включает язык запросов — для запросов используйте search_query.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Поисковый запрос"},
                    "version": {"type": "string", "description": "Версия платформы, опционально"},
                    "max_results": {"type": "integer", "description": "Макс. результатов", "default": 20},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_object_api",
            description="Методы, свойства, события объекта 1С.",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string", "description": "Имя объекта: Запрос, Массив, Справочники"},
                    "version": {"type": "string", "description": "Версия платформы, опционально"},
                },
                "required": ["object_name"],
            },
        ),
        Tool(
            name="list_syntax",
            description="Список объектов по категории: object, type, structure, operator, global.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "object|type|structure|operator|global, опционально"},
                    "version": {"type": "string", "description": "Версия платформы, опционально"},
                },
                "required": [],
            },
        ),
        Tool(
            name="list_help_versions",
            description="Список доступных версий справки.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="get_query_syntax",
            description="Справка по языку запросов 1С: ключевые слова, функции, предложения. "
                        "Параметр name: 'ЕСТЬNULL', 'ГДЕ', 'ВЫБРАТЬ', 'ISNULL', 'WhereStatement'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "RU-имя, EN-имя или topic_id"},
                    "version": {"type": "string", "description": "Версия платформы, опционально"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="search_query",
            description="Полнотекстовый поиск по справке языка запросов 1С (не BSL).",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Поисковый запрос"},
                    "version": {"type": "string", "description": "Версия платформы, опционально"},
                    "max_results": {"type": "integer", "description": "Макс. результатов", "default": 20},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="list_query_topics",
            description="Список тем справки языка запросов. category: keyword|function|statement|operator|literal|article.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Подкатегория, опционально"},
                    "version": {"type": "string", "description": "Версия платформы, опционально"},
                },
                "required": [],
            },
        ),
        Tool(
            name="validate_code",
            description="Проверка кода 1С на некорректные вызовы методов. Ищет вызовы Объект.Метод(), которых нет в API объекта. Например: Справочники.Х.Создать() — ошибка, нужен СоздатьЭлемент() или СоздатьГруппу().",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Текст кода 1С для проверки"},
                    "version": {"type": "string", "description": "Версия платформы, опционально"},
                    "max_errors": {"type": "integer", "description": "Макс. число ошибок в отчёте", "default": 50},
                },
                "required": ["code"],
            },
        ),
        Tool(
            name="create_processor",
            description="Конструктор метаданных: создать проект внешней обработки.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Имя обработки (идентификатор 1С)"},
                    "synonym": {"type": "string", "description": "Синоним на русском"},
                },
                "required": ["name", "synonym"],
            },
        ),
        Tool(
            name="set_attributes",
            description="Конструктор: задать объектные реквизиты внешней обработки.",
            inputSchema={
                "type": "object",
                "properties": {
                    "processor": {"type": "string", "description": "Имя обработки"},
                    "attributes": {
                        "type": "array",
                        "description": "Реквизиты: [{name, type_raw, qualifiers?}]",
                        "items": {"type": "object"},
                    },
                },
                "required": ["processor", "attributes"],
            },
        ),
        Tool(
            name="set_form",
            description="Конструктор: задать форму (поля, группы, команды, события). Параметры соответствуют build_form_layout.",
            inputSchema={
                "type": "object",
                "properties": {
                    "processor": {"type": "string", "description": "Имя обработки"},
                    "fields": {"type": "array", "items": {"type": "object"}, "description": "Плоские поля формы"},
                    "groups": {"type": "array", "items": {"type": "object"}, "description": "Группы и таблицы"},
                    "commands": {"type": "array", "items": {"type": "object"}, "description": "Команды формы"},
                    "events": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "События формы: [{event, handler}] — напр. {event: 'OnOpen', handler: 'ПриОткрытии'}",
                    },
                },
                "required": ["processor"],
            },
        ),
        Tool(
            name="set_module_code",
            description="Конструктор: задать текст модуля (ObjectModule или FormModule).",
            inputSchema={
                "type": "object",
                "properties": {
                    "processor": {"type": "string", "description": "Имя обработки"},
                    "module": {"type": "string", "description": "ObjectModule или FormModule"},
                    "code": {"type": "string", "description": "Текст модуля BSL"},
                },
                "required": ["processor", "module", "code"],
            },
        ),
        Tool(
            name="validate_project",
            description="Конструктор: проверить проект (XML-структура, BSL, наличие обработчиков команд/событий).",
            inputSchema={
                "type": "object",
                "properties": {
                    "processor": {"type": "string", "description": "Имя обработки"},
                    "version": {"type": "string", "description": "Версия справки для BSL-проверки, опционально"},
                },
                "required": ["processor"],
            },
        ),
        Tool(
            name="export_project",
            description="Конструктор: экспортировать внешнюю обработку. path — родительский каталог; "
                        "файлы пишутся в path/<ИмяОбработки>/ (корневой XML: path/<Имя>/<Имя>.xml).",
            inputSchema={
                "type": "object",
                "properties": {
                    "processor": {"type": "string", "description": "Имя обработки"},
                    "path": {
                        "type": "string",
                        "description": "Родительский каталог экспорта (не каталог самой обработки)",
                    },
                },
                "required": ["processor", "path"],
            },
        ),
        Tool(
            name="create_report",
            description="Конструктор: создать проект внешнего отчёта. kind=skd (по умолчанию) — отчёт на СКД "
                        "(запрос+поля+layout, без своей формы). kind=macet — отчёт на макете: свои реквизиты/"
                        "табличные части вместо параметров СКД, своя управляемая форма, макет из областей "
                        "(ПолучитьОбласть/Вывести в модуле). См. set_report_attributes, set_report_tabular_sections, "
                        "set_report_form, set_report_template для kind=macet.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Имя отчёта (идентификатор 1С)"},
                    "synonym": {"type": "string", "description": "Синоним на русском"},
                    "kind": {"type": "string", "description": "skd (по умолчанию) или macet", "default": "skd"},
                },
                "required": ["name", "synonym"],
            },
        ),
        Tool(
            name="set_report_attributes",
            description="Конструктор (kind=macet): задать собственные реквизиты отчёта — заменяют параметры СКД "
                        "(поля отбора/периода/флаги на самом объекте отчёта). Форма считывает и передаёт их напрямую.",
            inputSchema={
                "type": "object",
                "properties": {
                    "report": {"type": "string", "description": "Имя отчёта"},
                    "attributes": {
                        "type": "array",
                        "description": "Реквизиты: [{name, type_raw, synonym_ru?, qualifiers?}]",
                        "items": {"type": "object"},
                    },
                },
                "required": ["report", "attributes"],
            },
        ),
        Tool(
            name="set_report_tabular_sections",
            description="Конструктор (kind=macet): задать табличные части отчёта — для многострочных параметров "
                        "(напр. список организаций, список периодов), как Организации/ПериодыОтчета на ФТ_ОтчетБДР.",
            inputSchema={
                "type": "object",
                "properties": {
                    "report": {"type": "string", "description": "Имя отчёта"},
                    "tabular_sections": {
                        "type": "array",
                        "description": "[{name, synonym_ru?, attributes: [{name, type_raw, ...}]}]",
                        "items": {"type": "object"},
                    },
                },
                "required": ["report", "tabular_sections"],
            },
        ),
        Tool(
            name="set_report_form",
            description="Конструктор (kind=macet): задать управляемую форму отчёта (поля, группы, таблицы, "
                        "команды, события). Форма — своя (не платформенная общая форма СКД). Параметры как у set_form.",
            inputSchema={
                "type": "object",
                "properties": {
                    "report": {"type": "string", "description": "Имя отчёта"},
                    "form_name": {"type": "string", "description": "Имя формы (идентификатор), по умолчанию «Форма»"},
                    "form_synonym": {"type": "string", "description": "Синоним формы"},
                    "fields": {"type": "array", "items": {"type": "object"}, "description": "Плоские поля формы"},
                    "groups": {"type": "array", "items": {"type": "object"}, "description": "Группы и таблицы"},
                    "commands": {"type": "array", "items": {"type": "object"}, "description": "Команды формы"},
                    "events": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "События формы: [{event, handler}]",
                    },
                    "spreadsheet_fields": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Поле(-я) табличного документа для показа результата: [{name, title_ru?, "
                                       "events?}] — обычно одно, [{name: 'ТабДок'}]. Это единственный способ "
                                       "показать в форме ТабДок.Вывести(...); обычное поле (fields) для этого "
                                       "не подходит (реквизит должен быть типа ТабличныйДокумент).",
                    },
                },
                "required": ["report"],
            },
        ),
        Tool(
            name="set_report_template",
            description="Конструктор (kind=macet): задать табличный макет отчёта — именованные области строк, "
                        "заполняемые в модуле через Макет.ПолучитьОбласть(\"Имя\")/ТабДок.Вывести(Область, Уровень). "
                        "Свобода колонок/группировок обеспечивается количеством областей и BSL-кодом, а не схемой.",
            inputSchema={
                "type": "object",
                "properties": {
                    "report": {"type": "string", "description": "Имя отчёта"},
                    "template_name": {"type": "string", "description": "Имя макета, по умолчанию «Макет»"},
                    "areas": {
                        "type": "array",
                        "description": "[{name, rows: [[{col, text?|parameter?, colspan?, bold?, align?, "
                                       "border?, number_format?}, ...], ...]}]",
                        "items": {"type": "object"},
                    },
                },
                "required": ["report", "areas"],
            },
        ),
        Tool(
            name="set_report_skd",
            description="Конструктор: задать схему компоновки данных отчёта (запрос, поля, параметры, итоги, макет). "
                        "Группировки и отбор — в layout (rows/columns/selection), не в тексте запроса.",
            inputSchema={
                "type": "object",
                "properties": {
                    "report": {"type": "string", "description": "Имя отчёта"},
                    "query": {"type": "string", "description": "Текст запроса набора данных"},
                    "fields": {
                        "type": "array",
                        "description": "Поля: [{data_path, title_ru?, role?, format_string?}]",
                        "items": {"type": "object"},
                    },
                    "parameters": {
                        "type": "array",
                        "description": "Параметры СКД: [{name, value_type, title_ru?, use_restriction?, expression?, "
                                       "use?, value_list_allowed?, default_value?, default_nil?, "
                                       "default_standard_period?}]. Канонический период (не пишите &Период.ДатаНачала "
                                       "в тексте запроса): Период (v8:StandardPeriod, use=Always, "
                                       "default_standard_period=true) + НачалоПериода/КонецПериода (xs:dateTime, "
                                       "use_restriction=true, expression=&Период.ДатаНачала / &Период.ДатаОкончания) "
                                       "— в тексте запроса используйте &НачалоПериода/&КонецПериода.",
                        "items": {"type": "object"},
                    },
                    "calculated_fields": {
                        "type": "array",
                        "items": {"type": "object"},
                    },
                    "totals": {
                        "type": "array",
                        "description": "Итоговые поля: [{data_path, expression}]",
                        "items": {"type": "object"},
                    },
                    "layout": {
                        "type": "object",
                        "description": "Макет, архетип по mode (или по форме, если mode не указан): "
                                       "mode=group_with_details — {group_by: [{field, group_type?}, ...], selection, "
                                       "filter_items?, data_parameters?} — сгруппированный список с детальными "
                                       "строками; несколько полей в group_by дают вложенные уровни группировки с "
                                       "подытогами на каждом уровне (напр. Исполнитель, затем Задача) — "
                                       "для группировки+детализации используйте это, НЕ pivot_table. "
                                       "mode=pivot_table — {rows, columns, selection, ...} — сводная таблица, "
                                       "обязательны и rows, и columns. mode=flat — {selection, ...} — плоский список.",
                    },
                },
                "required": ["report"],
            },
        ),
        Tool(
            name="set_report_module_code",
            description="Конструктор: задать текст модуля отчёта. module=ObjectModule (по умолчанию) — "
                        "СведенияОВнешнейОбработке и серверная логика. module=FormModule — модуль формы "
                        "(kind=macet; напр. обработчик команды «Сформировать»).",
            inputSchema={
                "type": "object",
                "properties": {
                    "report": {"type": "string", "description": "Имя отчёта"},
                    "code": {"type": "string", "description": "Текст модуля BSL"},
                    "module": {"type": "string", "description": "ObjectModule (по умолчанию) или FormModule", "default": "ObjectModule"},
                },
                "required": ["report", "code"],
            },
        ),
        Tool(
            name="validate_report",
            description="Конструктор: проверить внешний отчёт (XML СКД, BSL).",
            inputSchema={
                "type": "object",
                "properties": {
                    "report": {"type": "string", "description": "Имя отчёта"},
                    "version": {"type": "string", "description": "Версия справки для BSL-проверки, опционально"},
                },
                "required": ["report"],
            },
        ),
        Tool(
            name="export_report",
            description="Конструктор: экспортировать внешний отчёт. path — родительский каталог; "
                        "файлы пишутся в path/<ИмяОтчёта>/ (корневой XML: path/<Имя>/<Имя>.xml).",
            inputSchema={
                "type": "object",
                "properties": {
                    "report": {"type": "string", "description": "Имя отчёта"},
                    "path": {
                        "type": "string",
                        "description": "Родительский каталог экспорта",
                    },
                },
                "required": ["report", "path"],
            },
        ),
        Tool(
            name="describe",
            description="Конструктор: словарь возможностей сеттеров (reflection-справка). "
                        "unit — крупная единица (сейчас 'dcs'); name — раздел (напр. 'filter', "
                        "'selection'). Без name — обзор разделов. Отдаёт поля с типами/enum, "
                        "пример и рекомендации для сборки payload (напр. отборов СКД). "
                        "Не путать со справкой по BSL/языку запросов (get_syntax, get_query_syntax).",
            inputSchema={
                "type": "object",
                "properties": {
                    "unit": {"type": "string", "description": "Единица: dcs"},
                    "name": {"type": "string", "description": "Раздел единицы, напр. filter (опционально)"},
                },
                "required": ["unit"],
            },
        ),
    ])


def _format_response(text: str, structured: dict | None = None) -> str:
    """Format response with optional JSON block."""
    parts = [text]
    if structured:
        parts.append("\n\n--- JSON ---\n" + json.dumps(structured, ensure_ascii=False, indent=2))
    return "\n".join(parts)


def _format_validate_project(result: dict) -> str:
    if result.get("ok"):
        return _format_response("Проект прошёл проверку.", result)
    lines = ["Проект не прошёл проверку:"]
    for e in result.get("library_errors", []):
        lines.append(f"  XML: {e}")
    for e in result.get("bsl_errors", []):
        mod = e.get("module", "")
        if e.get("kind") == "unknown_object":
            lines.append(
                f"  BSL [{mod}] строка {e['line']}: {e['object']}.{e['method']}() — {e.get('message', '')}"
            )
        else:
            lines.append(
                f"  BSL [{mod}] строка {e['line']}: {e['object']}.{e['method']}() — метод не найден"
            )
    for h in result.get("missing_handlers", []):
        lines.append(f"  Обработчик не найден в FormModule: {h}")
    return _format_response("\n".join(lines), result)


async def _dispatch(name: str, arguments: dict) -> list[TextContent]:
    if name == "get_syntax":
        result = tools.get_syntax(
            name=arguments["name"],
            version=arguments.get("version"),
        )
        if result:
            text = _format_response(
                result.get("text", ""),
                result.get("structured"),
            )
        else:
            text = f"Не найдено: {arguments['name']}"
        return [TextContent(type="text", text=text)]

    if name == "search_syntax":
        results = tools.search_syntax(
            query=arguments["query"],
            version=arguments.get("version"),
            max_results=arguments.get("max_results", 20),
        )
        text = json.dumps(results, ensure_ascii=False, indent=2) if results else "Ничего не найдено"
        return [TextContent(type="text", text=text)]

    if name == "get_object_api":
        result = tools.get_object_api(
            object_name=arguments["object_name"],
            version=arguments.get("version"),
        )
        text = json.dumps(result, ensure_ascii=False, indent=2) if result else f"Объект не найден: {arguments['object_name']}"
        return [TextContent(type="text", text=text)]

    if name == "list_syntax":
        results = tools.list_syntax(
            category=arguments.get("category"),
            version=arguments.get("version"),
        )
        text = json.dumps(results, ensure_ascii=False, indent=2) if results else "Пусто (загрузите справку)"
        return [TextContent(type="text", text=text)]

    if name == "list_help_versions":
        versions = tools.list_versions()
        text = "Доступные версии:\n" + "\n".join(versions) if versions else "Нет загруженных справок"
        return [TextContent(type="text", text=text)]

    if name == "get_query_syntax":
        result = tools.get_query_syntax(
            name=arguments["name"],
            version=arguments.get("version"),
        )
        if result:
            text = _format_response(
                result.get("description") or result.get("syntax") or "",
                result,
            )
        else:
            text = f"Не найдено: {arguments['name']}"
        return [TextContent(type="text", text=text)]

    if name == "search_query":
        results = tools.search_query(
            query=arguments["query"],
            version=arguments.get("version"),
            max_results=arguments.get("max_results", 20),
        )
        text = json.dumps(results, ensure_ascii=False, indent=2) if results else "Ничего не найдено"
        return [TextContent(type="text", text=text)]

    if name == "list_query_topics":
        results = tools.list_query_topics(
            category=arguments.get("category"),
            version=arguments.get("version"),
        )
        text = json.dumps(results, ensure_ascii=False, indent=2) if results else "Пусто (загрузите shquery_ru)"
        return [TextContent(type="text", text=text)]

    if name == "describe":
        result = dcs_vocabulary.describe(arguments["unit"], arguments.get("name"))
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    if name == "validate_code":
        errors = tools.validate_code(
            code=arguments["code"],
            version=arguments.get("version"),
            max_errors=arguments.get("max_errors", 50),
        )
        if not errors:
            text = "Ошибок не найдено."
        else:
            lines = [f"Найдено {len(errors)} предполагаемых ошибок:"]
            for e in errors:
                if e.get("kind") == "unknown_object":
                    lines.append(f"  Строка {e['line']}: {e['object']}.{e['method']}() — {e.get('message', 'объект не найден в справке')}")
                else:
                    sug = f" → возможно: {e['suggestion']}" if e.get("suggestion") and "проверьте" not in str(e.get("suggestion", "")) else ""
                    lines.append(f"  Строка {e['line']}: {e['object']}.{e['method']}() — метод не найден в {e.get('api_object', '')}{sug}")
            text = "\n".join(lines)
        return [TextContent(type="text", text=text)]

    if name == "create_processor":
        result = constructor_tools.create_processor(
            name=arguments["name"],
            synonym=arguments["synonym"],
        )
        text = _format_response(
            f"Создана обработка «{result['name']}» ({result['synonym_ru']}).",
            result,
        )
        return [TextContent(type="text", text=text)]

    if name == "set_attributes":
        result = constructor_tools.set_attributes(
            processor=arguments["processor"],
            attributes=arguments["attributes"],
        )
        text = _format_response(
            f"Реквизиты обработки «{result['name']}» обновлены ({len(result['attributes'])} шт.).",
            result,
        )
        return [TextContent(type="text", text=text)]

    if name == "set_form":
        result = constructor_tools.set_form(
            processor=arguments["processor"],
            fields=arguments.get("fields"),
            groups=arguments.get("groups"),
            commands=arguments.get("commands"),
            events=arguments.get("events"),
        )
        text = _format_response(f"Форма обработки «{result['name']}» обновлена.", result)
        return [TextContent(type="text", text=text)]

    if name == "set_module_code":
        result = constructor_tools.set_module_code(
            processor=arguments["processor"],
            module=arguments["module"],
            code=arguments["code"],
        )
        text = _format_response(
            f"Модуль {result['module']} обработки «{result['name']}» сохранён ({result['code_length']} симв.).",
            result,
        )
        return [TextContent(type="text", text=text)]

    if name == "validate_project":
        result = constructor_tools.validate_project(
            processor=arguments["processor"],
            version=arguments.get("version"),
        )
        text = _format_validate_project(result)
        return [TextContent(type="text", text=text)]

    if name == "export_project":
        result = constructor_tools.export_project(
            processor=arguments["processor"],
            path=arguments["path"],
        )
        files = "\n".join(f"  - {f}" for f in result["files"])
        text = _format_response(
            f"Экспорт «{result['processor']}»:\n"
            f"  каталог обработки: {result['processor_dir']}\n"
            f"  открыть в Конфигураторе: {result['open_in_configurator']}\n"
            f"Файлы (относительно {result['parent_dir']}):\n{files}",
            result,
        )
        return [TextContent(type="text", text=text)]

    if name == "create_report":
        result = constructor_tools.create_report(
            name=arguments["name"],
            synonym=arguments["synonym"],
            kind=arguments.get("kind", "skd"),
        )
        text = _format_response(
            f"Создан отчёт «{result['name']}» ({result['synonym_ru']}), kind={result['kind']}.",
            result,
        )
        return [TextContent(type="text", text=text)]

    if name == "set_report_attributes":
        result = constructor_tools.set_report_attributes(
            report=arguments["report"],
            attributes=arguments["attributes"],
        )
        text = _format_response(
            f"Реквизиты отчёта «{result['name']}» обновлены ({len(result['attributes'])} шт.).",
            result,
        )
        return [TextContent(type="text", text=text)]

    if name == "set_report_tabular_sections":
        result = constructor_tools.set_report_tabular_sections(
            report=arguments["report"],
            tabular_sections=arguments["tabular_sections"],
        )
        text = _format_response(
            f"Табличные части отчёта «{result['name']}» обновлены ({len(result['tabular_sections'])} шт.).",
            result,
        )
        return [TextContent(type="text", text=text)]

    if name == "set_report_form":
        result = constructor_tools.set_report_form(
            report=arguments["report"],
            form_name=arguments.get("form_name"),
            form_synonym=arguments.get("form_synonym"),
            fields=arguments.get("fields"),
            groups=arguments.get("groups"),
            commands=arguments.get("commands"),
            events=arguments.get("events"),
            spreadsheet_fields=arguments.get("spreadsheet_fields"),
        )
        text = _format_response(f"Форма «{result['form_name']}» отчёта «{result['name']}» обновлена.", result)
        return [TextContent(type="text", text=text)]

    if name == "set_report_template":
        result = constructor_tools.set_report_template(
            report=arguments["report"],
            areas=arguments["areas"],
            template_name=arguments.get("template_name"),
        )
        text = _format_response(
            f"Макет «{result['template_name']}» отчёта «{result['name']}» обновлён ({result['area_count']} областей).",
            result,
        )
        return [TextContent(type="text", text=text)]

    if name == "set_report_skd":
        result = constructor_tools.set_report_skd(
            report=arguments["report"],
            query=arguments.get("query"),
            fields=arguments.get("fields"),
            parameters=arguments.get("parameters"),
            calculated_fields=arguments.get("calculated_fields"),
            totals=arguments.get("totals"),
            layout=arguments.get("layout"),
        )
        text = _format_response(
            f"СКД отчёта «{result['name']}» обновлена "
            f"({result['field_count']} полей, layout={'да' if result['has_layout'] else 'нет'}).",
            result,
        )
        return [TextContent(type="text", text=text)]

    if name == "set_report_module_code":
        result = constructor_tools.set_report_module_code(
            report=arguments["report"],
            code=arguments["code"],
            module=arguments.get("module", "ObjectModule"),
        )
        text = _format_response(
            f"{result['module']} отчёта «{result['name']}» сохранён ({result['code_length']} симв.).",
            result,
        )
        return [TextContent(type="text", text=text)]

    if name == "validate_report":
        result = constructor_tools.validate_report(
            report=arguments["report"],
            version=arguments.get("version"),
        )
        text = _format_validate_project(result)
        return [TextContent(type="text", text=text)]

    if name == "export_report":
        result = constructor_tools.export_report(
            report=arguments["report"],
            path=arguments["path"],
        )
        files = "\n".join(f"  - {f}" for f in result["files"])
        text = _format_response(
            f"Экспорт отчёта «{result['report']}»:\n"
            f"  каталог: {result['report_dir']}\n"
            f"  открыть в Конфигураторе: {result['open_in_configurator']}\n"
            f"Файлы (относительно {result['parent_dir']}):\n{files}",
            result,
        )
        return [TextContent(type="text", text=text)]

    return [TextContent(type="text", text=f"Неизвестный инструмент: {name}")]


def _response_bytes(response: list[TextContent] | None) -> int | None:
    """Serialized response size for the journal (sum of TextContent utf-8 bytes)."""
    if not response:
        return None
    total = 0
    for item in response:
        text = getattr(item, "text", None)
        if text:
            total += len(text.encode("utf-8"))
    return total or None


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    args = arguments or {}
    started_at = utc_now_iso()
    started_mono = time.monotonic()
    success = True
    error_code = None
    response: list[TextContent] | None = None

    try:
        response = await _dispatch(name, args)
        return response
    except Exception as e:
        success = False
        error_code = type(e).__name__
        response = [TextContent(type="text", text=f"Ошибка: {mask_secrets(str(e))}")]
        return response
    finally:
        _call_logger.log(
            tool=name,
            started_at=started_at,
            started_mono=started_mono,
            args=args,
            success=success,
            error_code=error_code,
            result_bytes=_response_bytes(response),
        )


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
