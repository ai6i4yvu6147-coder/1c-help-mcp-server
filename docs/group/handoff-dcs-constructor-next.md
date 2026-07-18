# Хэндофф: конструктор СКД — следующие шаги

Самодостаточное ТЗ для нового чата. Здесь весь нужный контекст — не требует пересказа.
Для деталей идти в перечисленные дизайн-доки. Дата: 2026-07-18.

---

## 0. Кластер и направление

Три репозитория, единый движок формата 1С-XML:

- **`1c-metadata-schema`** (`onec_metadata_schema`) — библиотека: `parse`/`validate`/
  `serialize` + `build_*`. Единый источник знания формата **на чтение и запись**.
- **`1c-config-mcp`** (C-MCP) — read-потребитель: индексирует конфигурации в SQLite,
  MCP-запросы. Политика: read-only.
- **`1c-help-mcp`** (H-MCP) — write-потребитель: конструктор объектов (`constructor.db`) +
  справка BSL/языка запросов + reflection-справка конструктора (`describe`).

Реальные выгрузки XML (источник истины формата): `C:\Users\Alex\Documents\1`.
СКД-примеры: `Фитэра\Задачник` (СКД на Catalog/Document), `Трансгаз\Бухгалтерия Кашпур
разработка\ТД_ОперативныйУчет` (СКД отчётов).

## 1. Что уже сделано (с коммитами, всё в `main`)

**`1c-metadata-schema`:**
- `2f1ac78` — типизированные хелперы отбора/выборки: `build_dcs_filter_item`,
  `build_dcs_selection_item`, `COMPARISON_TYPES`; параметризованный `right`;
  `userSettingPresentation`; валидатор проверяет поля фильтра.
- `5d1ed3a` — `vocabulary.py` + `describe()`; `VIEW_MODES` + `view_mode` у фильтра.
- `7fca948` — секция `parameter` в словаре (+ guidance «параметры vs отборы»).

**`1c-help-mcp`:**
- `5642fc4` — дизайн-доки (`write-tools-taxonomy.md`, `describe-and-dcs-settings.md`).
- `8695ae2` — MCP-tool `describe` (обёртка над `vocabulary.describe`) + `dcs-best-practices.md`.
- `cf18f71` — статус best-practices.

**`1c-config-mcp`:**
- `0ff7170` — дизайн `dcs-schema-indexing.md` (read-сторона, ещё не реализовано).

**Подтверждено загрузкой в Конфигураторе:** внешний отчёт с отборами всех `right`-форм
открывается, отборы отображаются с верными типами (демо `scripts/build_dcs_filter_demo.py`).

Текущее состояние тестов библиотеки: **97 passed** (`pytest` в `1c-metadata-schema`).

## 2. Ключевые доменные факты (НЕ переоткрывать)

- **СКД — не только у отчётов.** Крепится к Catalog/Document/InformationRegister (тысячи в
  реальных базах). Из 146 схем: 144 имеют `<dataSet>`, 126 — `<query>` (86%), 2 — только
  настройки/параметры без набора.
- **Отбор — это шаблон.** Левая часть — любое поле, включая ссылочное (Организация — норма).
  Значение обычно НЕ зашивают: его наполняет пользователь в режиме предприятия. Выполняемая
  часть = фиксированные настройки схемы + пользовательские поверх. **Запрещающей валидации
  по значениям не делаем.**
- **Параметры vs отборы.** Параметр — для того, что меняет выборку на уровне СУБД:
  период/даты виртуальных таблиц остатков/оборотов (период отбором нельзя — СУБД посчитает
  на текущую дату, потом отфильтрует на сервере 1С = тормоза) и ветвящая логика (валюта
  учёта). Базовые реквизиты (Организация/Контрагент/Склад) — отбором, не `&Параметр` в `ГДЕ`.
  Уже в guidance `describe(unit='dcs', name='parameter')`.
- **Пользовательские настройки** (видимость на форме): `dcsset:userSettingID` (GUID —
  включает в польз. настройки) + `dcsset:viewMode` (`Auto`/`QuickAccess`/`Normal`/
  `Inaccessible`; `Auto` опускается; `QuickAccess` = сразу на форме). Дефолт-политика:
  основные отборы выносить (`QuickAccess` + `userSettingID`).
- **`right`-формы (подтверждены + загружены Конфигуратором):** `xs:string` (пустая),
  `v8:StandardBeginningDate` (variant Custom + date), `v8:ValueListType` (болванка для
  активного отбора), `dcscor:Field` (ссылка на другое поле СКД). Порядок дочерних в фильтре:
  `use? → left → comparisonType → right? → viewMode? → userSettingPresentation? → userSettingID?`.
- **Тестовая дисциплина.** Round-trip доказывает только внутреннюю согласованность; DCS
  reader round-trip на реальных файлах неполон (см. докстринг `dcs.py`). Поэтому проверка =
  `build → serialize → assert по реальному XML`, затем **загрузка в Конфигураторе** для всего,
  что трогает форму XML. Политика «расширяем от реальных выгрузок»: не выдумывать форму тега,
  сначала подтвердить на реальном файле.

## 3. Архитектурные принципы (держать)

- **Write-tools группируются по «единице редактирования»**, не по секции XML и не по виду
  объекта. Инвариант: **число tools не зависит от числа видов объектов/типов элементов**
  (новое = данные: значение `kind`, запись в словарь). Детали — `write-tools-taxonomy.md`.
- **Словарь — единый источник в библиотеке** (`vocabulary.py`), `describe` — тонкий
  сериализатор. Тест-инвариант «поля секции == параметры сигнатуры билдера» (в
  `tests/test_vocabulary.py`) — добавил аргумент билдеру без записи в словарь → CI падает.
- **C-MCP:** NO_DB_MIGRATIONS, при изменении схемы — bump `INDEXER_VERSION` и пересборка
  БД; всё за развилкой «старый путь / библиотека»; верификация по `testing-protocol.md`.
- **Перф-советы — только guidance, не запрещающая валидация** (зависят от СУБД/версии).

## 4. Следующие шаги (по приоритету)

### Шаг A — `build_dcs_order_item` (маленький, РАЗБЛОКИРОВАН)

Форма подтверждена на `ТД_ОперативныйУчет/Reports/ФТ_АвансыПоставщикам/Templates/
ОсновнаяСхемаКомпоновкиДанных`:

```xml
<dcsset:order>
    <dcsset:item xsi:type="dcsset:OrderItemField">
        <dcsset:field>Организация</dcsset:field>
        <dcsset:orderType>Asc</dcsset:orderType>   <!-- Asc | Desc -->
    </dcsset:item>
</dcsset:order>
```

- Добавить `build_dcs_order_item(field, *, direction='Asc')` + случай `auto=True`
  (`OrderItemAuto`).
- Энкодер `_encode_settings_variant`: явный `dcsset:order` с `OrderItemField` наряду с
  текущим `OrderItemAuto` (сейчас авто эмитится только внутри группировок).
- Секция `order` в `vocabulary.py` + инвариант-тест; guidance-пример.
- Тесты: build→serialize→assert; без-регресс на текущих (авто-порядок в группировках).

### Шаг B — консолидация таксономии write 15→~7 + `set_dcs` (крупный)

Полный дизайн — `write-tools-taxonomy.md`. Суть:
- Целевые ~7 tools: `create(kind)` · `validate` · `export` · `set_object` · `set_form` ·
  `set_dcs` · `set_template` · `set_module`. `kind` (`processor`/`report`/далее) — параметр,
  не семейство tools. Семантика «вызов = полная замена единицы» (билдер stateless).
- `set_dcs` **отвязать от отчёта** (крепится и к Catalog/Document).
- **`set_dcs` дефолты** (единственный незакрытый пункт best-practices): базовый реквизит →
  отбор + вынос в польз. настройки (`QuickAccess`); период → параметр (канонический трио
  `build_dcs_standard_period_params()` уже есть).
- Миграция H-MCP за развилкой: новые tools поверх `ConstructorTools`, старые `set_report_*`/
  `*_project` → адаптеры → удалить. Свести дубли в `shared/constructor/` (`export.py`+
  `export_report.py`, `validate.py`+`validate_report.py`). **Библиотеку не трогаем.**

### Шаг C — C-MCP read: `get_dcs_schema` + текст запроса → FTS (параллельно B)

Полный дизайн — `1c-config-mcp/docs/dcs-schema-indexing.md`. Суть:
- Два уровня, НЕ 6 таблиц: текст запроса набора → существующий FTS `code_search` (срез 1,
  86% схем имеют запрос; деградировать без запроса); полная семантика → одна таблица
  `dcs_schema` (blob) + `get_dcs_schema(object, template)` (срез 2) + shape-hint колонки
  (`has_query`, `dataset_count`, `filter_item_count`…).
- Через read-сторону `onec_metadata_schema.dcs` (reader round-trip неполон — расширять по
  месту), за развилкой, старый парсер не трогать (СКД он не читает — 0 регрессии).
- MXL-макеты — отдельный трек (форматно не пересекаются со СКД; единственный шов — СКД
  ссылается на макет оформления по имени через `outputParameters/МакетОформления`).

### Шаг D — остальные секции словаря + пробелы билдера (по мере надобности)

- Секции `describe`: `dataset`, `dataset_link`, `field`, `calculated_field`, `total_field`,
  `layout`, `role`, `output_parameter` (каждая с инвариант-тестом).
- **Пробелы билдера** (из best-practices, `dcs-best-practices.md`): `total_field` не
  принимает «Рассчитывать по…» (scope группировки итога); проверить/добавить «параметры
  связи» у `build_dcs_dataset_link`; набор данных «Объект» (ValueTable) с представлениями
  ссылочных полей (проблема N+1).

## 5. Ключевые файлы

**Дизайн:**
- `1c-help-mcp/docs/write-tools-taxonomy.md` — целевая поверхность write-tools.
- `1c-help-mcp/docs/describe-and-dcs-settings.md` — контракт `describe` + под-язык настроек.
- `1c-help-mcp/docs/dcs-best-practices.md` — best-practices СКД, размечены и привязаны.
- `1c-config-mcp/docs/dcs-schema-indexing.md` — read-сторона.
- `1c-config-mcp/docs/library-migration.md` — стратегия единого движка.

**Код:**
- `1c-metadata-schema/src/onec_metadata_schema/dcs.py` — `build_dcs_*`, энкодер
  (`_encode_settings_variant`, `_encode_filter_right`), `COMPARISON_TYPES`/`VIEW_MODES`.
- `1c-metadata-schema/src/onec_metadata_schema/vocabulary.py` — `VOCABULARY` + `describe()`.
- `1c-help-mcp/server/server.py` — MCP-tool `describe` (в `list_tools` и `_dispatch`).
- Тесты: `1c-metadata-schema/tests/test_dcs_builder.py`, `tests/test_vocabulary.py`.
- Демо/проверка Конфигуратором: `1c-metadata-schema/scripts/build_dcs_filter_demo.py`.

## 6. Как проверять

- `cd 1c-metadata-schema && pytest -q` (сейчас 97 passed).
- `describe` смоук: `python -c "import asyncio,json; import server.server as s;
  print(json.loads(asyncio.run(s._dispatch('describe',{'unit':'dcs'}))[0].text))"` в
  `1c-help-mcp`.
- Всё, что меняет форму XML → сборка демо + ручная загрузка в Конфигураторе.

## 7. Рекомендуемый порядок

A (быстрый разблокированный) → затем B **или** C (независимы, можно параллельно). D — по
мере надобности. При старте B держать инвариант «tools не растут» и не трогать библиотеку.
