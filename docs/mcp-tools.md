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
| `create_processor` | Конструктор: создать проект внешней обработки |
| `set_attributes` | Конструктор: объектные реквизиты `[{name, type_raw, qualifiers?}]` |
| `set_form` | Конструктор: форма (fields, groups, commands, events: [{event, handler}]) |
| `set_module_code` | Конструктор: текст модуля (`ObjectModule` или `FormModule`) |
| `validate_project` | Конструктор: XML + BSL + обработчики команд/событий |
| `export_project` | Конструктор: экспорт; `path` = родительский каталог, обработка → `path/<Name>/` |

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

### Конструктор метаданных (внешние обработки)

Последовательность для `TestPoryadkaDemo`:

1. `create_processor(name="TestPoryadkaDemo", synonym="Тест порядка UI (demo)")`
2. `set_attributes(processor="TestPoryadkaDemo", attributes=[{"name":"Орг","type_raw":"cfg:CatalogRef.Организации"},{"name":"ФИО","type_raw":"xs:string","qualifiers":{"length":10,"allowed_length":"Variable"}}])`
3. `set_form(processor="TestPoryadkaDemo", fields=[...], events=[{"event":"OnOpen","handler":"ПриОткрытии"}])` — events экспортируются в Form.xml
4. `set_module_code(processor="TestPoryadkaDemo", module="FormModule", code="")` — опционально
5. `validate_project(processor="TestPoryadkaDemo")`
6. `export_project(processor="TestPoryadkaDemo", path="C:/temp/export")` → открыть `C:/temp/export/TestPoryadkaDemo/TestPoryadkaDemo.xml`

#### Каталог экспорта (`export_project.path`)

`path` — **родительский каталог**, куда складываются обработки. Каждая обработка получает **свою подпапку** с именем обработки. Несколько обработок в одном `path` не смешиваются.

Пример: `path="C:/fullAI"`, обработка `HelloWorld`:

```
C:/fullAI/
  HelloWorld/
    HelloWorld.xml          ← открыть в Configurator
    HelloWorld/
      Forms/Форма.xml
      Forms/Форма/Ext/Form.xml
      Forms/Форма/Ext/Form/Module.bsl
      Ext/ObjectModule.bsl  (если задан)
```

Configurator ищет формы по `<каталог_xml>/<Имя>/Forms/...`. Агент передаёт `path=C:/fullAI`; сервер создаёт `C:/fullAI/HelloWorld/HelloWorld.xml` и `C:/fullAI/HelloWorld/HelloWorld/Forms/...`.

События формы: `events=[{"event":"OnOpen","handler":"ПриОткрытии"}, ...]` — экспортируются в `Form.xml`.

Состояние проектов хранится в `constructor.db` (отдельно от справки). Канон: `docs/metadata-constructor-plan.md`.

### Ограничения `validate_code`

- Regex-поиск вызовов, не полный парсер BSL.
- Ложные срабатывания возможны на динамических вызовах.
- Коллекции метаданных (`Справочники.Имя.Метод`) проверяются по шаблонному менеджеру (`СправочникМенеджер`).

### Где в коде

- Регистрация: `server/server.py`
- Справка: `server/tools.py`
- Конструктор: `server/constructor_tools.py`, `shared/constructor/`
