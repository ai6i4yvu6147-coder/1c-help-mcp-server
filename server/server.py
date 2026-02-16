"""MCP server for 1C syntax help."""
import asyncio
import json
import sys
from pathlib import Path
from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio

sys.path.insert(0, str(Path(__file__).parent.parent))

from server.tools import HelpTools

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
app = Server("1c-help-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_syntax",
            description="Справка по синтаксису 1С: метод, свойство, тип, конструкция, глобальная функция. "
                        "Параметр name: например 'Запрос.Выполнить', 'Сообщить', 'Если', 'Строка'. "
                        "Возвращает текст и структурированный JSON (signature, params, returns).",
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
            description="Полнотекстовый поиск по справке 1С.",
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
    ]


def _format_response(text: str, structured: dict | None = None) -> str:
    """Format response with optional JSON block."""
    parts = [text]
    if structured:
        parts.append("\n\n--- JSON ---\n" + json.dumps(structured, ensure_ascii=False, indent=2))
    return "\n".join(parts)


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
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

        return [TextContent(type="text", text=f"Неизвестный инструмент: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Ошибка: {e}")]


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
