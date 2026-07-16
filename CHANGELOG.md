# Лог доработок

---

## 2026-07-16

- **Чтение журнала + первый Admin-Hub CLI (protocol v1.0.7 §3.4):** новый `admin_tool/cli.py` с подкомандой `tool-calls` (первый CLI у help-mcp) — JSON-конверт `{module, moduleType, db, query, count, rows[]}` (camelCase, UTF-8 без BOM), newest-first, фильтры `--task-id/--tool/--since/--until/--only-errors/--limit/--offset`; нет БД/таблицы → `count:0, rows:[]`. Читалка `read_tool_calls()` — в общем `shared/tool_calls_log.py` (идентична копиям config/data). Упаковка: `module.manifest.example.json` (`runtime.cliExe: Tools/1c-help-cli.exe`) + `build_all.bat` теперь собирает `1c-help-cli.exe` (onefile) и кладёт его + манифест + каталог `logs/` в Portable. Проверено standalone-скриптом и собранным exe (pytest в venv нет).

- **Журнал вызовов инструментов `logs/tool-calls.db` + опциональная корреляция `task_id`/`agent`/`model` (protocol v1.0.7 §3, кластерно-единообразно):** каждый вызов MCP-инструмента пишет одну строку в SQLite `logs/tool-calls.db` (schema `tool_calls` из аддендума: `ts_utc`, `tool`, `task_id`, `agent`, `model`, `elapsed_ms`, `result_bytes`, `success`, `error_code`, `args_summary`, `pid`). Диспетчер `call_tool` разбит на чистый `_dispatch` (бросает исключения) и обёртку с таймингом + журналированием в `finally` — **failure-isolated** (ошибки записи глотаются, результат инструмента не меняется). Централизованная обработка ошибок в обёртке (текст «Ошибка: …» теперь проходит `mask_secrets`) вместо прежнего `try/except` вокруг всей цепочки. Все инструменты advertise опциональную тройку `task_id`/`agent`/`model` (никогда не в `required`) через общий `shared/tool_calls_log.py::CORRELATION_INPUT_PROPERTIES`; серверо-специфичный скоуп (`version`/…) — внутри маскированного и обрезанного до 2 КБ `args_summary`, ключ `password` редактируется. Новые `shared/security.py` (`mask_secrets`) и `shared/tool_calls_log.py` идентичны копиям в `1c-data-mcp`/`1c-config-mcp` (отличие — путь импорта `mask_secrets`). Тесты: `tests/test_tool_calls_log.py` (в репозитории нет pytest — набор добавлен для единообразия; логика проверена standalone-скриптом + смоук-тестом сервера: все 24 инструмента отдают тройку, error-path журналируется).

## 2026-07-12

- **Re-normalize 2.6.0 (Sub):** канон WI 2.6.0 — хаб-модель без `protocol-ref/`, `protocol-snapshot.py` и полей epoch/dispute_round; Sub читает `docs/group/shared/` на Head по `head.path`; agent-cache docs обновлены; layout без изменений (1 agent + 4 skills); состояние протокола (`stable`, `last_event` 20260711T053100Z) без изменений.

## 2026-07-11

- **Конструктор отчётов: второй архетип «на макете» (`kind=macet`) + починка `kind=skd`.** `report` в `constructor.db` расширен (`kind`, реквизиты/табличные части/форма/макет отчёта); 4 новых MCP tools (`set_report_attributes`, `set_report_tabular_sections`, `set_report_form`, `set_report_template`); `create_report`/`set_report_module_code` — параметры `kind`/`module`. `export_report.py` — вторая ветка экспорта (`Forms/`, `Templates/<макет>/Ext/Template.xml`, `Ext/ObjectModule.bsl`, `Forms/<форма>/Ext/Form/Module.bsl`). Заодно починен реальный блокер в `kind=skd`: `set_report_skd`'s `layout` был жёстко привязан к `build_dcs_table_layout` (только сводная таблица) — обычный сгруппированный список нельзя было построить через MCP вообще; теперь `layout.mode` (`group_with_details`/`pivot_table`/`flat`) диспетчерится в нужный `build_dcs_*_layout`. Плюс `default_standard_period` для параметра `Период`. Оба архетипа подтверждены сквозными сборками через реальные MCP tools (проект Задачник, `ТрудозатратыПоИсполнителям`/`ТрудозатратыПоИсполнителямМакет`) — macet-версия потребовала трёх фиксов на стороне библиотеки `1c-metadata-schema` (см. её CHANGELOG/`docs/group/handoff-layout-report.md`). `constructor.db` дважды пересоздавалась под новую схему (правило `no-db-migrations`). Документация: `docs/group/handoff-layout-report.md` (новый), `handoff-external-report-skd.md` и `docs/mcp-tools.md` обновлены.
- **Конструктор метаданных (Stage E):** подсистема `shared/constructor/` + `constructor.db`; 6 MCP tools (`create_processor`, `set_attributes`, `set_form`, `set_module_code`, `validate_project`, `export_project`); экспорт через `onec-metadata-schema`; зависимость в `requirements.txt`, PyInstaller hidden-imports.

## 2026-07-02

- **Re-normalize 2.4.0 (Sub):** канон WI 2.4.0 — agent-cache tier на английском (`agent_docs_lang: en`); entry-point docs через doc-librarian; deprecations registry (пути 2.2.0/2.3.0 — уже отсутствуют); `docs/canons/` — English copy из WI; layout без изменений (1 agent + 4 skills); состояние протокола (`stable`, epoch 0, `protocol-ref`) без изменений.

## 2026-07-01

- **Re-normalize 2.3.0 (Sub):** layout 2 agents→1 (`doc-librarian`); skills 9→4 (`normalize-project`, `canon-align`, `maintain-docs`, `sync` — единый skill вместо 7 legacy group-sync); удалён `sync-relay.py`; добавлены `docs/group/OPERATOR-HANDOFF.md`, `docs/group/templates/`; entry-point docs через doc-librarian. Состояние протокола (`stable`, epoch 0, `protocol-ref`) без изменений.

## 2026-06-30

- **Re-normalize 2.2.1 (Sub):** layout субагентов 4→2 (`doc-librarian`, `group-sync-arbitrator`); `canon-align` и `process-group-inbox` — только skills; обновлены каноны `normalize-governance` (1.2.0), `group-sync`; `.arbitration/` убран из `.gitignore`; entry-point docs через doc-librarian.
- **Нормализация (Sub):** роль subordinate в группе `1c-cursor`, Head `1c-admin-tool`; `group.manifest.yaml`, `docs/group/integration.md`, `docs/canons/`, group-sync scripts и `.cursor/` skills/agents.
- **Документация:** `readme.txt` → `README.md`; обновлены `AGENTS.md`, `docs/agent-onboarding.md`, `docs/README.md`, `docs/architecture.md`, `README_AI.md`; добавлены `docs/group/integration.md`, `docs/canons/README.md`, `docs/todo.md`, `docs/normalize-record.md`; правки по ревью doc-librarian (порядок чтения, inbox в todo, карта группы Head).
- **Зависимости:** в `requirements.txt` добавлен `pyyaml>=6.0` (скрипты group-sync); продуктовые пакеты сохранены.

## 2026-06-08

- **Язык запросов (shquery_ru)**: парсер `shared/query_parser.py`; импорт ~118 тем в БД (`category`: `query_*`, `parent_name` = topic_id); MCP tools `get_query_syntax`, `search_query`, `list_query_topics`.
- **Разделение поиска**: `search_syntax` / `get_syntax` / `get_object_api` / `list_syntax` исключают `query_*`; `search_query` / `get_query_syntax` — только язык запросов.
- **Документация и структура проекта**: добавлены `docs/` (onboarding, architecture, mcp-tools, database, testing-protocol), `AGENTS.md`, `README_AI.md`; обновлены `readme.txt`, `.gitignore`; удалён `scripts/test_tools.py`.
- **MCP tools**: улучшен `search_syntax` — приоритет точного совпадения `name` и `full_name` над широким FTS; `list_syntax(category="global")` возвращает функции глобального контекста; `get_syntax` для одноимённых методов предпочитает «Глобальный контекст».
- **Admin GUI**: кнопка «Обновить справку» — пересоздание выбранной версии из сохранённого или нового пути; путь источника хранится в `meta.source_path`.
- **Парсер**: `help_parser.py` — обход вложенных каталогов методов (`methods/catalog*/`) через `rglob`; после обновления справки через Admin улучшается наполнение глобальных функций (описания, сигнатуры).
