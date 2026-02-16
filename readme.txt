================================================================================
1C Help MCP Server
================================================================================

Справка по синтаксису 1С для ИИ-агентов (синтакс-помощник и валидация кода).

БЫСТРЫЙ СТАРТ
-------------
1. Сборка: build_all.bat → в родительской папке создаётся 1c_help_mcp_server_Portable (готовый продукт).
2. В Portable: Admin.bat → "Добавить справку" → папка с shcntx_ru и shlang_ru → версия (8.3.27).
3. MCP: в конфиг клиента добавить "command": "ПУТЬ\\1c_help_mcp_server_Portable\\Server\\1c-help-server.exe".
4. Инструменты: get_syntax, search_syntax, get_object_api, validate_code, list_syntax.

СТРУКТУРА ПРОЕКТА (только исходники)
------------------------------------
admin_tool/   - GUI администратора
server/       - MCP сервер
shared/       - парсер, db_manager, version_resolver
scripts/      - test_tools.py (проверка tools)
config.json   - при разработке: databases_dir (папка databases создаётся локально или не используется)
build_all.bat - сборка; результат в ..\1c_help_mcp_server_Portable\, не в проекте.

ИСТОЧНИК СПРАВКИ
----------------
Распакуйте shcntx_ru.hbk и shlang_ru.hbk из C:\Program Files\1cv8\<версия>\bin\
(7zip: правый клик → Распаковать)
