## База данных (SQLite)

### Главное правило: NO_DB_MIGRATIONS

В этом проекте **никогда** не пишутся миграции, конвертации или скрипты «обновления» существующих `databases/*.db`.

Базы — производный артефакт от распакованной справки. После изменений парсера/схемы база **пересоздаётся** через Admin («Добавить справку» с перезаписью версии).

### Как БД создаётся

1. Admin → «Добавить справку» → папка с `shcntx_ru` / `shlang_ru` / `shquery_ru` → версия (например `8.3.27.1688`).
2. `admin_tool/importer.py` создаёт файл `databases/help_<version>.db`.

### Схема

- `meta` — версия, дата создания.
- `syntax_objects` — объекты, типы, конструкции, темы языка запросов.
  - BSL: `category` = object, type, structure.
  - Запросы: `category` = query_keyword, query_function, query_statement, query_operator, query_literal, query_article.
  - `parent_name` — `topic_id` темы запроса (имя файла в `shquery_ru`).
- `syntax_methods` — методы, свойства, события; для запросов — одна запись с синтаксисом, примером, `see_also` в `params_json`.
- `help_search` (FTS5) — индекс для `search_syntax` и `search_query` (name, full_name, signature, description).
- `meta.has_query_help`, `meta.query_topics_count` — флаг и счётчик тем запросов.

### constructor.db (конструктор метаданных)

Отдельная БД рядом со справкой: `{databases_dir}/constructor.db`. Та же политика NO_DB_MIGRATIONS — схема создаётся при первом открытии, не мигрируется.

- `processor` — проект внешней обработки: имя, синоним, JSON-спеки формы и реквизитов.
- `module` — тексты модулей (`ObjectModule`, `FormModule`) по имени обработки.
- `report` — проект внешнего отчёта; `kind` (`skd` по умолчанию или `macet`) определяет, какие поля актуальны:
  - `skd`: `schema_name`, `query_text`, `fields_json`, `parameters_json`, `calculated_json`, `totals_json`, `layout_json`.
  - `macet`: `attributes_json`, `tabular_sections_json`, `form_name`/`form_synonym_ru`/`form_fields_json`/`form_groups_json`/`form_commands_json`/`form_events_json`/`form_spreadsheet_fields_json`, `template_name`/`template_areas_json`.
- `report_module` — тексты модулей отчёта (`ObjectModule`; `FormModule` только для `kind=macet`) по имени отчёта.

Экспорт через библиотеку `onec_metadata_schema` (СКД: 3 XML; макет: `Forms/`+`Templates/`+опциональные `.bsl`, до 7 файлов). См. `docs/metadata-constructor-plan.md`, `docs/mcp-tools.md`, `docs/group/handoff-external-report-skd.md`, `docs/group/handoff-layout-report.md`.

### Версии платформы

Имя файла: `help_8_3_27_1688.db` (точки → подчёркивания).  
Выбор БД: `shared/version_resolver.py` — точное совпадение или ближайшая версия.
