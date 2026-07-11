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
| `create_report` | Конструктор: создать проект отчёта; `kind=skd` (по умолчанию) или `kind=macet` |
| `set_report_skd` | Конструктор (`kind=skd`): запрос, поля, параметры, итоги, `layout` (архетип по `layout.mode`) |
| `set_report_attributes` | Конструктор (`kind=macet`): объектные реквизиты вместо параметров СКД |
| `set_report_tabular_sections` | Конструктор (`kind=macet`): табличные части (многострочные параметры) |
| `set_report_form` | Конструктор (`kind=macet`): своя форма (fields, groups, commands, events, `spreadsheet_fields`) |
| `set_report_template` | Конструктор (`kind=macet`): табличный макет — именованные области строк |
| `set_report_module_code` | Конструктор: текст модуля отчёта (`ObjectModule` по умолчанию; `FormModule` для `kind=macet`) |
| `validate_report` | Конструктор: XML (СКД или макет) + BSL |
| `export_report` | Конструктор: экспорт; `path` = родительский каталог, отчёт → `path/<Name>/` |

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

### Конструктор отчётов (внешние отчёты)

Два архетипа, выбираются через `create_report(kind=...)`. Подробности и уроки первых реальных сборок — `docs/group/handoff-external-report-skd.md` (СКД) и `docs/group/handoff-layout-report.md` (макет).

#### `kind=skd` — на схеме компоновки данных

Для отчётов с группировкой/сводом по запросу без своей формы.

1. `create_report(name="ТрудозатратыПоИсполнителям", synonym="Трудозатраты по исполнителям")` — `kind` по умолчанию `skd`
2. `set_report_skd(report=..., query=..., fields=[...], parameters=[...период-трио...], totals=[{"data_path":"Часы","expression":"Сумма(Часы)"}], layout={"group_by":[{"field":"Исполнитель"},{"field":"Задача"}], "selection":[...]})`
   - `layout.mode`: `group_with_details` (список с группировкой + подытоги на каждом уровне — несколько полей в `group_by` дают вложенные уровни, не один составной ключ), `pivot_table` (нужны и `rows`, и `columns`), `flat`. Без `mode` архетип определяется по форме объекта.
   - Канонический период: параметр `Период` (`v8:StandardPeriod`, `use:"Always"`, `default_standard_period:true`) + `НачалоПериода`/`КонецПериода` (`xs:dateTime`, `use_restriction:true`, `expression:"&Период.ДатаНачала"`/`"&Период.ДатаОкончания"`); в тексте запроса — `&НачалоПериода`/`&КонецПериода`, не `&Период.ДатаНачала` напрямую.
3. `set_report_module_code(report=..., code="...")` — `ObjectModule`, `СведенияОВнешнейОбработке()`
4. `validate_report(report=...)`
5. `export_report(report=..., path=...)`

#### `kind=macet` — на табличном макете

Для отчётов со своей формой и напечатанным макетом (нет DCS вообще).

1. `create_report(name=..., synonym=..., kind="macet")`
2. `set_report_attributes(report=..., attributes=[{"name":"НачалоПериода","type_raw":"xs:dateTime","qualifiers":{"date_fractions":"Date"}}, ...])` — вместо параметров СКД
3. `set_report_tabular_sections(report=..., tabular_sections=[...])` — опционально, для многострочных параметров (список организаций и т.п.)
4. `set_report_form(report=..., form_name="ФормаОтчета", fields=[...], commands=[{"name":"Сформировать"}], spreadsheet_fields=[{"name":"ТабДок"}], events=[...])` — **`spreadsheet_fields` обязателен**: без него результату негде отобразиться (обычное `fields`-поле для `ТабличныйДокумент` не подходит)
5. `set_report_template(report=..., areas=[{"name":"Шапка","rows":[[{"col":0,"text":"...","bold":true}]]}, ...])` — именованные области; группировки/отступы — не в макете, а в BSL (`Область.Уровень`, `НачатьАвтогруппировкуСтрок`)
6. `set_report_module_code(report=..., module="ObjectModule", code="...")` — данные + заливка макета; экспортировать **функцию**, возвращающую `ТабличныйДокумент` (см. ниже)
7. `set_report_module_code(report=..., module="FormModule", code="...")` — вызов команды «Сформировать»
8. `validate_report(report=...)`
9. `export_report(report=..., path=...)`

**BSL-паттерн (важно):** `Перем ТабДок Экспорт` на `ObjectModule` + чтение `Объект.ТабДок` из `FormModule` после вызова `Объект.Метод()` — ненадёжно (не факт, что форма увидит то же серверное состояние объекта). Рабочий паттерн — функция с `Возврат`, вызываемая через `РеквизитФормыВЗначение`:

```bsl
// ObjectModule
Функция СформироватьНаСервере() Экспорт
	ТабДок = Новый ТабличныйДокумент;
	... ТабДок.Вывести(Макет.ПолучитьОбласть("Шапка")) ...
	Возврат ТабДок;
КонецФункции

// FormModule
&НаСервере
Процедура СформироватьНаСервере()
	ТабДок = РеквизитФормыВЗначение("Объект").СформироватьНаСервере();
КонецПроцедуры
```

### Ограничения `validate_code`

- Regex-поиск вызовов, не полный парсер BSL.
- Ложные срабатывания возможны на динамических вызовах.
- Коллекции метаданных (`Справочники.Имя.Метод`) проверяются по шаблонному менеджеру (`СправочникМенеджер`).

### Где в коде

- Регистрация: `server/server.py`
- Справка: `server/tools.py`
- Конструктор: `server/constructor_tools.py`, `shared/constructor/`
