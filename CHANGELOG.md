# Лог доработок

---

## 2026-07-11

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
