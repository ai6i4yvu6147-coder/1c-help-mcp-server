# Лог доработок

---

## 2026-06-08

- **Язык запросов (shquery_ru)**: парсер `shared/query_parser.py`; импорт ~118 тем в БД (`category`: `query_*`, `parent_name` = topic_id); MCP tools `get_query_syntax`, `search_query`, `list_query_topics`.
- **Разделение поиска**: `search_syntax` / `get_syntax` / `get_object_api` / `list_syntax` исключают `query_*`; `search_query` / `get_query_syntax` — только язык запросов.
- **Документация и структура проекта**: добавлены `docs/` (onboarding, architecture, mcp-tools, database, testing-protocol), `AGENTS.md`, `README_AI.md`; обновлены `readme.txt`, `.gitignore`; удалён `scripts/test_tools.py`.
- **MCP tools**: улучшен `search_syntax` — приоритет точного совпадения `name` и `full_name` над широким FTS; `list_syntax(category="global")` возвращает функции глобального контекста; `get_syntax` для одноимённых методов предпочитает «Глобальный контекст».
- **Admin GUI**: кнопка «Обновить справку» — пересоздание выбранной версии из сохранённого или нового пути; путь источника хранится в `meta.source_path`.
- **Парсер**: `help_parser.py` — обход вложенных каталогов методов (`methods/catalog*/`) через `rglob`; после обновления справки через Admin улучшается наполнение глобальных функций (описания, сигнатуры).
