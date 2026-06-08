================================================================================
1C Help MCP Server
================================================================================

  Для ИИ и разработчиков: см. docs/ (начать с docs/agent-onboarding.md).

Справка по синтаксису 1С для ИИ-агентов (синтакс-помощник и валидация кода).

БЫСТРЫЙ СТАРТ
-------------
1. Сборка: build_all.bat → в соседней папке создаётся 1c_help_mcp_server_Portable.
2. В Portable: Admin.bat → «Добавить справку» → папка с shcntx_ru и shlang_ru → версия (8.3.27).
3. MCP: в конфиг клиента добавить command на Server\1c-help-server.exe внутри portable-папки.
4. Инструменты: get_syntax, search_syntax, get_object_api, validate_code, list_syntax, list_help_versions.

СТРУКТУРА ПРОЕКТА (исходники)
------------------------------
admin_tool/   - GUI администратора
server/       - MCP сервер
shared/       - парсер, db_manager, version_resolver
docs/         - документация для ИИ и разработчиков
config.json   - dev: databases_dir = databases
build_all.bat - сборка → ../1c_help_mcp_server_Portable/

ИСТОЧНИК СПРАВКИ
----------------
Распакуйте shcntx_ru.hbk и shlang_ru.hbk из каталога bin платформы 1С (7zip: Распаковать).
Путь к распакованным папкам указывается в Admin при импорте — в репозиторий не кладётся.

ПОРТАТИВНОСТЬ
-------------
Portable можно переносить. После переноса обновите путь к exe в конфиге MCP-клиента.
