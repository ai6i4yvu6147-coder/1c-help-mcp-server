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
| `describe` | Reflection-справка конструктора: `unit` (`dcs`) + `name` (12 разделов: `dataset`/`dataset_link`/`field`/`role`/`calculated_field`/`total_field`/`parameter`/`output_parameter`/`filter`/`selection`/`order`/`layout`); без `name` — обзор. Поля/enum/пример для сборки payload. Не путать со справкой BSL |
| `create` | Конструктор: создать проект. `kind`: `processor`/`report`; `archetype` (report): `skd`/`macet` |
| `set_object` | Конструктор: объектная оболочка — реквизиты `[{name, type_raw, qualifiers?}]` и (отчёт) табличные части |
| `set_form` | Конструктор: форма (fields, groups, commands, events: [{event, handler}]; отчёт: form_name/spreadsheet_fields) |
| `set_dcs` | Конструктор: схема СКД — запрос, поля, параметры, итоги, `layout` (архетип по `layout.mode`) |
| `set_template` | Конструктор: табличный макет (MXL) — именованные области строк |
| `set_module` | Конструктор: текст модуля (`ObjectModule` или `FormModule`) |
| `validate` | Конструктор: XML + BSL + обработчики команд/событий |
| `export` | Конструктор: экспорт; `path` = родительский каталог, проект → `path/<Name>/` |

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

### Конструктор: унифицированная поверхность

Группировка по «единице редактирования» (дизайн — [`write-tools-taxonomy.md`](write-tools-taxonomy.md)).
`project` — единый хэндл (имя ищется в обеих таблицах `processor`/`report`, `kind`
определяется автоматически). Один вызов `set_*` = **полная замена** этой единицы (билдер
stateless). Payload полей СКД (отбор/выборка/порядок) — через `describe(unit='dcs')`.

| Tool | Единица | Сигнатура |
|---|---|---|
| `create` | lifecycle | `create(kind, name, synonym, archetype?)` — `kind`: `processor`/`report`; `archetype` (report): `skd`/`macet` |
| `set_object` | объектная оболочка | `set_object(project, attributes?, tabular_sections?)` |
| `set_form` | форма | `set_form(project, fields?, groups?, commands?, events?, form_name?, form_synonym?, spreadsheet_fields?)` |
| `set_dcs` | схема СКД | `set_dcs(project, query?, fields?, parameters?, calculated_fields?, totals?, layout?)` — крепится и к Catalog/Document (Stage G) |
| `set_template` | макет MXL | `set_template(project, areas, template_name?)` |
| `set_module` | код | `set_module(project, module, code)` |
| `validate` | lifecycle | `validate(project, version?)` |
| `export` | lifecycle | `export(project, path)` |

**Инвариант:** число write-tools не зависит от числа видов объектов/типов элементов —
новое = данные (значение `kind`, запись в `describe`), не новый tool.

Отложено: свести дубли `shared/constructor/` (`export.py`+`export_report.py`,
`validate.py`+`validate_report.py`) в один модуль с ветвлением по `kind`; мульти-набор в
`set_dcs` (`datasets`/`dataset_links` — сейчас один запрос+поля); `set_dcs`-дефолты
(базовый реквизит → отбор+`QuickAccess`, период → параметр-трио).

### Конструктор метаданных (внешние обработки)

Последовательность для `TestPoryadkaDemo`:

1. `create(kind="processor", name="TestPoryadkaDemo", synonym="Тест порядка UI (demo)")`
2. `set_object(project="TestPoryadkaDemo", attributes=[{"name":"Орг","type_raw":"cfg:CatalogRef.Организации"},{"name":"ФИО","type_raw":"xs:string","qualifiers":{"length":10,"allowed_length":"Variable"}}])`
3. `set_form(project="TestPoryadkaDemo", fields=[...], events=[{"event":"OnOpen","handler":"ПриОткрытии"}])` — events экспортируются в Form.xml
4. `set_module(project="TestPoryadkaDemo", module="FormModule", code="")` — опционально
5. `validate(project="TestPoryadkaDemo")`
6. `export(project="TestPoryadkaDemo", path="C:/temp/export")` → открыть `C:/temp/export/TestPoryadkaDemo/TestPoryadkaDemo.xml`

#### Каталог экспорта (`export.path`)

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

Два архетипа, выбираются через `create(kind="report", archetype=...)`. Подробности и уроки первых реальных сборок — `docs/group/handoff-external-report-skd.md` (СКД) и `docs/group/handoff-layout-report.md` (макет).

#### `archetype=skd` — на схеме компоновки данных

Для отчётов с группировкой/сводом по запросу без своей формы.

1. `create(kind="report", name="ТрудозатратыПоИсполнителям", synonym="Трудозатраты по исполнителям")` — `archetype` по умолчанию `skd`
2. `set_dcs(project=..., query=..., fields=[...], standard_period=true, totals=[{"data_path":"Часы","expression":"Сумма(Часы)"}], layout={"group_by":[{"field":"Исполнитель"},{"field":"Задача"}], "selection":[...]})`
   - `layout.mode`: `group_with_details` (список с группировкой + подытоги на каждом уровне — несколько полей в `group_by` дают вложенные уровни, не один составной ключ), `pivot_table` (нужны и `rows`, и `columns`), `flat`. Без `mode` архетип определяется по форме объекта.
   - Отбор/выборка/порядок — в `layout` (`filter_items`/`selection`/`order_items`); контракт полей — `describe(unit='dcs')`. Основные отборы выносите в польз. настройки: `filter_items=[{"field":"Организация","comparison":"Equal","view_mode":"QuickAccess","generate_user_setting_id":true}]`.
   - **Несколько наборов данных:** вместо `query`/`fields` передайте `datasets=[{name, query, fields, data_source?}]` + `dataset_links=[{source_dataset, destination_dataset, source_expression, destination_expression, required?}]` (взаимоисключимо с `query`/`fields`). Guidance: предпочитайте один набор с `ЛЕВОЕ СОЕДИНЕНИЕ`; связь наборов — крайний случай (регистр+остатки).
   - **Канонический период:** проще всего `standard_period=true` — добавит трио `Период` (`v8:StandardPeriod`, `use:"Always"`) + `НачалоПериода`/`КонецПериода` (`xs:dateTime`, `use_restriction:true`, `expression:"&Период.ДатаНачала"`/`"&Период.ДатаОкончания"`) в параметры; в тексте запроса ссылайтесь на `&НачалоПериода`/`&КонецПериода`, не на `&Период.ДатаНачала` напрямую. Либо задайте эти параметры вручную через `parameters=[...]`.
3. `set_module(project=..., module="ObjectModule", code="...")` — `СведенияОВнешнейОбработке()`
4. `validate(project=...)`
5. `export(project=..., path=...)`

#### `archetype=macet` — на табличном макете

Для отчётов со своей формой и напечатанным макетом (нет DCS вообще).

1. `create(kind="report", name=..., synonym=..., archetype="macet")`
2. `set_object(project=..., attributes=[{"name":"НачалоПериода","type_raw":"xs:dateTime","qualifiers":{"date_fractions":"Date"}}, ...])` — реквизиты вместо параметров СКД; для многострочных параметров (список организаций и т.п.) добавьте `tabular_sections=[...]` тем же вызовом
3. `set_form(project=..., form_name="ФормаОтчета", fields=[...], commands=[{"name":"Сформировать"}], spreadsheet_fields=[{"name":"ТабДок"}], events=[...])` — **`spreadsheet_fields` обязателен**: без него результату негде отобразиться (обычное `fields`-поле для `ТабличныйДокумент` не подходит)
4. `set_template(project=..., areas=[{"name":"Шапка","rows":[[{"col":0,"text":"...","bold":true}]]}, ...])` — именованные области; группировки/отступы — не в макете, а в BSL (`Область.Уровень`, `НачатьАвтогруппировкуСтрок`)
5. `set_module(project=..., module="ObjectModule", code="...")` — данные + заливка макета; экспортировать **функцию**, возвращающую `ТабличныйДокумент` (см. ниже)
6. `set_module(project=..., module="FormModule", code="...")` — вызов команды «Сформировать»
7. `validate(project=...)`
8. `export(project=..., path=...)`

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
