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
            name="set_form",
            description="Конструктор: задать форму обработки ИЛИ отчёта (поля, группы, команды, события). "
                        "project — единый хэндл (обработка или отчёт). Для отчёта доступны "
                        "form_name/form_synonym/spreadsheet_fields (своя управляемая форма макетного отчёта). "
                        "Детали payload (поля/группы/команды/события) — describe(unit='form').",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "Имя проекта (обработка или отчёт)"},
                    "fields": {
                        "type": "array", "items": {"type": "object"},
                        "description": "Плоские поля формы: [{name, type_raw, kind?}] — kind "
                                       "input|checkbox|radio|attribute (attribute — безголовый "
                                       "реквизит формы без элемента). См. describe(unit='form', name='field').",
                    },
                    "groups": {"type": "array", "items": {"type": "object"}, "description": "Группы, таблицы, вкладки (describe(unit='form', name='group'))"},
                    "commands": {"type": "array", "items": {"type": "object"}, "description": "Команды формы + кнопки (describe(unit='form', name='command'))"},
                    "events": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "События формы: [{event, handler}] — напр. {event: 'OnOpen', handler: 'ПриОткрытии'}",
                    },
                    "form_name": {"type": "string", "description": "Только отчёт: имя формы (по умолчанию «Форма»)"},
                    "form_synonym": {"type": "string", "description": "Только отчёт: синоним формы"},
                    "spreadsheet_fields": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Только отчёт (kind=macet): поле(-я) табличного документа для показа "
                                       "результата: [{name, title_ru?, events?}]. Обязательно для показа "
                                       "ТабДок.Вывести(...).",
                    },
                },
                "required": ["project"],
            },
        ),
        Tool(
            name="create",
            description="Конструктор: создать проект. kind — вид объекта: "
                        "processor (внешняя обработка) или report (внешний отчёт). archetype — только "
                        "для report: skd (по умолчанию, отчёт на СКД) или macet (отчёт на макете).",
            inputSchema={
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "description": "processor или report"},
                    "name": {"type": "string", "description": "Имя проекта (идентификатор 1С)"},
                    "synonym": {"type": "string", "description": "Синоним на русском"},
                    "archetype": {"type": "string", "description": "Только report: skd (по умолчанию) или macet"},
                },
                "required": ["kind", "name", "synonym"],
            },
        ),
        Tool(
            name="set_object",
            description="Конструктор: объектная оболочка проекта — реквизиты объекта и (для отчёта) "
                        "табличные части. Один вызов = полная замена оболочки. "
                        "Реквизит ОБЪЕКТА (здесь) ≠ реквизит формы (set_form). Payload — describe(unit='object').",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "Имя проекта (обработка или отчёт)"},
                    "attributes": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Реквизиты: [{name, type_raw, synonym_ru?, qualifiers?}]",
                    },
                    "tabular_sections": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Только отчёт: табличные части [{name, synonym_ru?, attributes:[...]}]",
                    },
                },
                "required": ["project"],
            },
        ),
        Tool(
            name="set_dcs",
            description="Конструктор: схема компоновки данных (СКД) отчёта — запрос, поля, "
                        "параметры, вычисляемые/итоговые поля, layout. СКД поддержана только для отчётов "
                        "(report); обработку собирают БЕЗ СКД — set_object + set_form + set_module. "
                        "Группировки, отбор и сортировка — в layout "
                        "(rows/columns/selection/filter_items/order_items), не в тексте запроса. "
                        "Payload полей отбора/порядка — см. describe(unit='dcs').",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "Имя проекта (отчёт)"},
                    "query": {"type": "string", "description": "Текст запроса единственного набора данных"},
                    "fields": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Поля единственного набора: [{data_path, title_ru?, role?, format_string?}]",
                    },
                    "datasets": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Несколько наборов (взаимоисключимо с query/fields): "
                                       "[{name, query, fields, data_source?}]. Имена наборов — для dataset_links.",
                    },
                    "dataset_links": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Связи наборов: [{source_dataset, destination_dataset, "
                                       "source_expression, destination_expression, required?}].",
                    },
                    "parameters": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Параметры СКД (канонический период — см. describe или standard_period).",
                    },
                    "standard_period": {
                        "type": "boolean",
                        "description": "Добавить канонический период-трио (Период + НачалоПериода/КонецПериода) "
                                       "в параметры. В тексте запроса ссылайтесь на &НачалоПериода/&КонецПериода.",
                    },
                    "calculated_fields": {"type": "array", "items": {"type": "object"}},
                    "totals": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Итоговые поля: [{data_path, expression}]",
                    },
                    "layout": {
                        "type": "object",
                        "description": "Макет, архетип по mode: group_with_details | pivot_table | flat "
                                       "(отбор/сортировка — filter_items/order_items; см. describe(unit='dcs')).",
                    },
                },
                "required": ["project"],
            },
        ),
        Tool(
            name="set_template",
            description="Конструктор: табличный макет (MXL) проекта — именованные области "
                        "строк. Отчёты (archetype=macet).",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "Имя проекта (отчёт)"},
                    "template_name": {"type": "string", "description": "Имя макета, по умолчанию «Макет»"},
                    "areas": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "[{name, rows: [[{col, text?|parameter?, colspan?, bold?, ...}], ...]}]",
                    },
                },
                "required": ["project", "areas"],
            },
        ),
        Tool(
            name="set_module",
            description="Конструктор: текст модуля обработки или отчёта (ObjectModule — модуль "
                        "объекта с произвольными процедурами; FormModule — модуль формы, обработчики "
                        "команд и событий).",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "Имя проекта (обработка или отчёт)"},
                    "module": {"type": "string", "description": "ObjectModule или FormModule"},
                    "code": {"type": "string", "description": "Текст модуля BSL"},
                },
                "required": ["project", "module", "code"],
            },
        ),
        Tool(
            name="patch_module",
            description="Конструктор: точечная правка модуля обработки/отчёта — замена фрагмента "
                        "BSL (аналог str_replace/Edit), без пересылки всего модуля. old меняется на "
                        "new по точному совпадению; old должен встречаться РОВНО один раз (иначе "
                        "добавьте контекст в old или передайте replace_all=true). Модуль должен быть "
                        "предварительно создан через set_module.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "Имя проекта (обработка или отчёт)"},
                    "module": {"type": "string", "description": "ObjectModule или FormModule"},
                    "old": {"type": "string", "description": "Заменяемый фрагмент (точное совпадение)"},
                    "new": {"type": "string", "description": "Новый фрагмент"},
                    "replace_all": {
                        "type": "boolean",
                        "description": "Заменить все вхождения old (по умолчанию false — требуется одно).",
                    },
                },
                "required": ["project", "module", "old", "new"],
            },
        ),
        Tool(
            name="validate",
            description="Конструктор: проверить проект — обработку или отчёт (XML-структура "
                        "метаданных + наличие процедур-обработчиков команд/событий формы). "
                        "Эвристическая BSL-проверка по справке отключена (давала массовый шум).",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "Имя проекта (обработка или отчёт)"},
                    "version": {"type": "string", "description": "Версия справки для BSL-проверки, опционально"},
                },
                "required": ["project"],
            },
        ),
        Tool(
            name="export",
            description="Конструктор: экспортировать проект — обработку или отчёт — в файлы для "
                        "Конфигуратора. path — родительский каталог; файлы пишутся в path/<Имя>/ "
                        "(корневой XML: path/<Имя>/<Имя>.xml).",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "Имя проекта (обработка или отчёт)"},
                    "path": {"type": "string", "description": "Родительский каталог экспорта"},
                },
                "required": ["project", "path"],
            },
        ),
        Tool(
            name="describe",
            description="Конструктор: словарь возможностей сеттеров (reflection-справка). "
                        "unit — крупная единица: 'dcs' (СКД отчёта), 'form' (форма обработки/отчёта: "
                        "поля, группы, команды, события; в т.ч. безголовый реквизит kind='attribute'), "
                        "'object' (реквизиты и табличные части объекта); name — раздел (напр. 'filter', "
                        "'field', 'command'). Без name — обзор разделов. Отдаёт поля с типами/enum, "
                        "пример и рекомендации для сборки payload. "
                        "Не путать со справкой по BSL/языку запросов (get_syntax, get_query_syntax).",
            inputSchema={
                "type": "object",
                "properties": {
                    "unit": {"type": "string", "description": "Единица: dcs | form | object"},
                    "name": {"type": "string", "description": "Раздел единицы, напр. filter/field/command (опционально)"},
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

    if name == "set_form":
        result = constructor_tools.set_form_any(
            arguments["project"],
            fields=arguments.get("fields"),
            groups=arguments.get("groups"),
            commands=arguments.get("commands"),
            events=arguments.get("events"),
            spreadsheet_fields=arguments.get("spreadsheet_fields"),
            form_name=arguments.get("form_name"),
            form_synonym=arguments.get("form_synonym"),
        )
        label = "отчёта" if result.get("kind") == "report" else "обработки"
        form_name = result.get("form_name")
        target = f"«{form_name}» {label} «{result['name']}»" if form_name else f"{label} «{result['name']}»"
        text = _format_response(f"Форма {target} обновлена.", result)
        return [TextContent(type="text", text=text)]

    if name == "create":
        result = constructor_tools.create(
            kind=arguments["kind"],
            name=arguments["name"],
            synonym=arguments["synonym"],
            archetype=arguments.get("archetype"),
        )
        if result["kind"] == "report":
            summary = (
                f"Создан отчёт «{result['name']}» ({result['synonym_ru']}), "
                f"archetype={result['archetype']}."
            )
        else:
            summary = f"Создана обработка «{result['name']}» ({result['synonym_ru']})."
        return [TextContent(type="text", text=_format_response(summary, result))]

    if name == "set_object":
        result = constructor_tools.set_object(
            project=arguments["project"],
            attributes=arguments.get("attributes"),
            tabular_sections=arguments.get("tabular_sections"),
        )
        parts = []
        if "attributes" in result:
            parts.append(f"реквизиты: {len(result['attributes'])}")
        if "tabular_sections" in result:
            parts.append(f"табличные части: {len(result['tabular_sections'])}")
        label = "отчёта" if result["kind"] == "report" else "обработки"
        summary = f"Оболочка {label} «{result['name']}» обновлена ({', '.join(parts)})."
        return [TextContent(type="text", text=_format_response(summary, result))]

    if name == "set_dcs":
        result = constructor_tools.set_dcs(
            project=arguments["project"],
            query=arguments.get("query"),
            fields=arguments.get("fields"),
            datasets=arguments.get("datasets"),
            dataset_links=arguments.get("dataset_links"),
            parameters=arguments.get("parameters"),
            calculated_fields=arguments.get("calculated_fields"),
            totals=arguments.get("totals"),
            layout=arguments.get("layout"),
            standard_period=arguments.get("standard_period", False),
        )
        summary = (
            f"СКД проекта «{result['name']}» обновлена "
            f"({result['dataset_count']} набор(ов), {result['field_count']} полей, "
            f"layout={'да' if result['has_layout'] else 'нет'})."
        )
        return [TextContent(type="text", text=_format_response(summary, result))]

    if name == "set_template":
        result = constructor_tools.set_template(
            project=arguments["project"],
            areas=arguments["areas"],
            template_name=arguments.get("template_name"),
        )
        summary = (
            f"Макет «{result['template_name']}» проекта «{result['name']}» обновлён "
            f"({result['area_count']} областей)."
        )
        return [TextContent(type="text", text=_format_response(summary, result))]

    if name == "set_module":
        result = constructor_tools.set_module(
            project=arguments["project"],
            module=arguments["module"],
            code=arguments["code"],
        )
        summary = (
            f"Модуль {result['module']} проекта «{result['name']}» сохранён "
            f"({result['code_length']} симв.)."
        )
        return [TextContent(type="text", text=_format_response(summary, result))]

    if name == "patch_module":
        result = constructor_tools.patch_module(
            project=arguments["project"],
            module=arguments["module"],
            old=arguments["old"],
            new=arguments["new"],
            replace_all=arguments.get("replace_all", False),
        )
        summary = (
            f"Модуль {result['module']} проекта «{result['name']}» пропатчен "
            f"({result['replacements']} замен(а), теперь {result['code_length']} симв.)."
        )
        return [TextContent(type="text", text=_format_response(summary, result))]

    if name == "validate":
        result = constructor_tools.validate(
            project=arguments["project"],
            version=arguments.get("version"),
        )
        return [TextContent(type="text", text=_format_validate_project(result))]

    if name == "export":
        result = constructor_tools.export(
            project=arguments["project"],
            path=arguments["path"],
        )
        files = "\n".join(f"  - {f}" for f in result["files"])
        summary = _format_response(
            f"Экспорт «{result['project']}»:\n"
            f"  каталог: {result['project_dir']}\n"
            f"  открыть в Конфигураторе: {result['open_in_configurator']}\n"
            f"Файлы (относительно {result['parent_dir']}):\n{files}",
            result,
        )
        return [TextContent(type="text", text=summary)]

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
