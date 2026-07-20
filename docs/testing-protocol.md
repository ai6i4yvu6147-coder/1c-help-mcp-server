## Протокол тестирования

Цель — проверять функциональность на **реальном MCP**, подключённом в IDE, без обходных Python-скриптов и прямого SQLite.

### Рабочий цикл

1. Агент правит исходники.
2. Пользователь пересобирает portable (`build_all.bat`), при изменении парсера — пересоздаёт БД через Admin.
3. Пользователь переподключает MCP в IDE.
4. Агент проверяет **вызовами MCP tools**.

### Чеклист (help-mcp)

1. `list_help_versions` — есть загруженная версия.
2. `get_syntax` — `Запрос.Выполнить`, `Сообщить`, `Строка`, `Если`.
3. `get_object_api` — `Запрос`, `Справочники`, `Массив`.
4. `list_syntax` — категории `object`, `type`, `global`.
5. `search_syntax` — `Выполнить` (ожидается `Запрос.Выполнить` в топе).

   (`validate_code` убран — эвристическая BSL-проверка отключена, см. `mcp-tools.md`.)

### Чеклист (query help, после импорта shquery_ru)

1. `list_query_topics(category="function")` — непустой список.
2. `get_query_syntax(name="ЕСТЬNULL")` — описание и пример.
3. `get_query_syntax(name="WhereStatement")` — поиск по topic_id.
4. `search_query(query="ГДЕ")` — `WhereStatement` в топе.
5. `search_query(query="ВЫБРАТЬ")` — ключевое слово, не BSL `Выбрать`.
6. `search_syntax(query="ВЫБРАТЬ")` — по-прежнему BSL-результаты.

### Чеклист (конструктор, Stage E)

1. `create_processor(name="TestPoryadkaDemo", synonym="Тест порядка UI (demo)")`
2. `set_attributes` — реквизиты `Орг`, `ФИО` (см. `docs/mcp-tools.md`)
3. `set_form` — поля `ЧСЛ`, `СТР`
4. `validate_project(processor="TestPoryadkaDemo")` — без ошибок
5. `export_project(processor="...", path="C:/fullAI")` → открыть `C:/fullAI/<Name>/<Name>.xml`; формы в `C:/fullAI/<Name>/<Name>/Forms/`

### Запрещено агенту

- Запускать `scripts/test_tools.py` или аналоги «вместо MCP».
- Создавать технические БД для «доказательства» работоспособности.
- Писать миграции SQLite (см. `database.md`).

### Если агент не может вызвать MCP tools

Сообщить пользователю и попросить выполнить вызовы вручную (минимум `list_help_versions` + целевой tool).
