## MCP tools

### Базовые правила

- Начинайте с `list_help_versions` — список загруженных версий справки.
- Параметр `version` опционален; без него берётся последняя (или `default_version` из config).
- Имя MCP-подключения в IDE может отличаться от имени exe.

### Инструменты

| Tool | Назначение |
|---|---|
| `list_help_versions` | Доступные версии справки |
| `get_syntax` | BSL: справка по имени `Запрос.Выполнить`, `Сообщить`, `Если` (без языка запросов) |
| `search_syntax` | BSL: полнотекстовый поиск (без тем `query_*`) |
| `get_object_api` | Методы/свойства объекта; `Справочники` → `СправочникМенеджер` |
| `list_syntax` | Список по категории: `object`, `type`, `structure`, `operator` (=structure), `global` |
| `get_query_syntax` | Справка по языку запросов: `ЕСТЬNULL`, `ГДЕ`, `ВЫБРАТЬ`, `WhereStatement` |
| `search_query` | Полнотекстовый поиск только по языку запросов |
| `list_query_topics` | Список тем запросов: `keyword`, `function`, `statement`, `operator`, `literal`, `article` |
| `validate_code` | Эвристика: вызовы `.Метод()`, которых нет в API объекта |

### Когда что использовать

- **BSL** (встроенный язык, объекты платформы) → `get_syntax`, `search_syntax`, `get_object_api`
- **Язык запросов** (текст `ВЫБРАТЬ … ГДЕ …`, функции `ЕСТЬNULL`) → `get_query_syntax`, `search_query`

### Примеры

- `get_syntax(name="Запрос.Выполнить")`
- `get_object_api(object_name="Массив")`
- `search_syntax(query="Выполнить", max_results=10)`
- `get_query_syntax(name="ЕСТЬNULL")`
- `get_query_syntax(name="WhereStatement")`
- `search_query(query="ГДЕ", max_results=5)`
- `list_query_topics(category="function")`
- `validate_code(code="Справочники.Х.Создать();")`

### Ограничения `validate_code`

- Regex-поиск вызовов, не полный парсер BSL.
- Ложные срабатывания возможны на динамических вызовах.
- Коллекции метаданных (`Справочники.Имя.Метод`) проверяются по шаблонному менеджеру (`СправочникМенеджер`).

### Где в коде

- Регистрация: `server/server.py`
- Реализация: `server/tools.py`
