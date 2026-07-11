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

Экспорт через библиотеку `onec_metadata_schema` (3 XML + опциональные `.bsl`). См. `docs/metadata-constructor-plan.md`.

### Версии платформы

Имя файла: `help_8_3_27_1688.db` (точки → подчёркивания).  
Выбор БД: `shared/version_resolver.py` — точное совпадение или ближайшая версия.
