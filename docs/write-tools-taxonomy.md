# Таксономия write-tools конструктора (H-MCP)

Проектная заметка. Фиксирует **целевую поверхность конструкторских MCP-инструментов**
и принцип, который не даёт ей разрастаться при добавлении новых видов объектов и типов
элементов. Расширяет [`metadata-constructor-plan.md`](metadata-constructor-plan.md)
(там — как устроен проект в `constructor.db`) и опирается на единый движок
`1c-metadata-schema` (см. `scope.md` там же).

Статус: **реализовано** (commit `63270e3`, 2026-07-18) — 15 → 8 унифицированных tools
(`create`/`set_object`/`set_form`/`set_dcs`/`set_template`/`set_module`/`validate`/`export`)
+ `describe`; актуальная поверхность — [`mcp-tools.md`](mcp-tools.md). Принцип, ради которого
таксономию замораживали: внешний контракт для агента фиксируем **раньше, чем расширяем
охват** (менять контракт после — дорого). Ниже — обоснование целевой поверхности (в силе
как проектный инвариант).

## Проблема: разрастание tools

Сейчас конструкторских tools — 15 (см. [`mcp-tools.md`](mcp-tools.md)). Причина — поверхность
форкается **по трём осям одновременно**:

- **по виду объекта** — семейство обработки (`set_attributes`, `set_form`,
  `set_module_code`, `validate_project`, `export_project`) **дублируется** семейством
  отчёта (`set_report_*`, `validate_report`, `export_report`);
- **по архетипу** — внутри отчёта развилка `kind=skd` vs `kind=macet` тянет свои
  сеттеры (`set_report_skd` vs `set_report_attributes` / `set_report_tabular_sections` /
  `set_report_template`);
- **по секции XML** — отдельный tool на реквизиты, форму, макет, модуль.

Три оси перемножаются. Форк проник и в реализацию: `shared/constructor/` содержит
дублирующие пары `export.py`/`export_report.py`, `validate.py`/`validate_report.py`.
Хуже симптома — **тренд**: каждый новый вид объекта (Stage G: `Catalog`/`Document` как
`Adopted`) при нынешней логике добавит `set_catalog_attributes`, `set_catalog_form`, …
Число tools растёт как произведение осей.

**Ключевой факт:** движок этот форк уже НЕ делает. В `scope.md` (Stage F):
`build_external_report` — «same builder as the DCS path, **extended rather than
forked**», `schema_name=None` выключает СКД. Расходятся именно tools; формат внизу
единый. MCP-слой развёл то, что библиотека свела.

## Принцип: группировка по единице редактирования

> Группируем tools **по «единице редактирования» агента**, не по секции XML и не по
> виду объекта.

Единиц столько, сколько сущностей агент держит в голове: **объектная оболочка**,
**форма**, **схема СКД**, **макет MXL**, **код модуля**. Вид объекта
(`processor` / `report` / далее `catalog`) и архетип (`skd` / `macet`) — это **не
семейства tools, а параметр `kind` + набор возможностей**, включаемых тем, какие
edit-tools вызваны. Нет схемы СКД — просто не звали `set_dcs` (ровно как
`schema_name=None` в билдере).

## Целевая поверхность (15 → ~7 + справка)

| Единица | Целевой tool | Схлопывает |
|---|---|---|
| lifecycle | `create(kind, name, synonym)` | `create_processor` + `create_report` |
| lifecycle | `validate(project)` | `validate_project` + `validate_report` |
| lifecycle | `export(project, path)` | `export_project` + `export_report` |
| объектная оболочка (GUID-слой) | `set_object(project, attributes, tabular_sections)` | `set_attributes` + `set_report_attributes` + `set_report_tabular_sections` |
| форма (любой элемент) | `set_form(project, fields, groups, tables, commands, events, spreadsheet_fields, …)` | `set_form` + `set_report_form` |
| схема СКД | `set_dcs(project, datasets, dataset_links, calculated, totals, parameters, layout)` | `set_report_skd` — **отвязать от отчёта** |
| макет MXL | `set_template(project, areas)` | `set_report_template` |
| код | `set_module(project, module, code)` | `set_module_code` + `set_report_module_code` |

`kind` при `create`: `processor` | `report` (далее — `catalog`/`document`/… на Stage G).
`project` — единый хэндл (в `constructor.db` уже лежит `kind`), заменяет пару
`processor=` / `report=`.

### Почему именно так резать

- **`set_dcs` и `set_template` раздельны** — это разные форматы, в библиотеке разные
  энкодеры (`dcs.py` vs `spreadsheet.py`). Настоящий шов, режем по нему.
- **`set_dcs` отвязан от отчёта.** СКД крепится и к `Catalog`/`Document`/
  `InformationRegister` (см. `dcs-schema-indexing.md` в C-MCP — их тысячи в реальных
  базах). «skd vs macet» — это не два вида объекта, а ортогональные возможности:
  «есть ли у объекта схема СКД» и «есть ли табличный макет».
- **Не скатываемся в один `set_everything`.** Мегатул с гигантским payload так же
  плох, как 15 tools: теряется инкрементальность и гранулярность валидации. ~7 единиц —
  сладкая точка.

### Семантика вызова: полная замена единицы

Билдер **stateless** — пересчитывает id/GUID из полного переданного списка (см.
`metadata-constructor-plan.md`). Отсюда контракт каждого `set_*`: **один вызов =
полная замена спеки этой единицы** (не патч/merge). Это единообразно, предсказуемо для
агента и совпадает с тем, как билдер уже работает.

## Недостающее звено: reflection-справка конструктора

Высокая абстракция обязана иметь противовес — **иначе агент угадывает payload**.
Сейчас справка есть только про **BSL/язык запросов** (`get_syntax`, `get_object_api`,
`get_query_syntax`). Вокабуляра **конструктора** нет: какие типы элементов формы есть,
какие поля берёт каждый, какие `layout.mode` у СКД, какие строки валидны в `type_raw`.

Вокабуляр уже существует машинно — это сигнатуры `build_*` в библиотеке. Нужен tool,
который их **отражает**:

- `describe(unit)` → для `form` — список типов элементов и их полей; для `dcs` —
  архетипы компоновки, роли, виды полей; для `object` — форма `type_raw` и
  квалификаторы.

Эффект двойной: (1) обобщённые сеттеры становятся безопасными; (2) справка
**саморастущая** — добавили в библиотеку `RadioButtonField`, он появляется в
`describe`, новый tool не нужен.

Детальный дизайн `describe` (контракт ответа, единый источник-словарь в библиотеке) +
хелперов под-языка настроек СКД (`build_dcs_filter_item`/`_selection_item`/`_order_item`):
[`describe-and-dcs-settings.md`](describe-and-dcs-settings.md).

## Проверка на реальных схемах (2026-07-18)

Прогон обоих дизайнов на 146 DCS-схемах (Фитэра/Задачник + Трансгаз/ТД_ОперативныйУчет).

**Подтверждено:**
- `set_dcs` отвязать от отчёта — верно: десятки Catalog несут схемы
  (`СКД_ПравилаОтбораСобытий`, `ВыборкаДанных`, `СКД`), это не фича отчёта.
- Библиотека уже покрывает частые случаи: `build_dcs_schema` принимает
  `datasets=None` (schema без набора данных — 2/146), `dataset_links` (мульти-набор:
  `ТД_ОтчетГлонасс` — 6 запросов / 8 источников / 10 итогов), calc/total/params, layouts
  flat/group/pivot. То есть `set_dcs` ложится на существующий API — библиотеку под
  типовые схемы дорабатывать не надо.

**Конкретное обоснование `describe` (главная находка):** доминирующее содержимое
каталожных схем — **под-язык настроек** (`dcsset:filter` с `comparisonType`/`left`/
`right`, `selection`, `order`, `groupItems`, `groupType`, `periodAddition`). В библиотеке
он сейчас принимается как **сырой `filter_items: list[dict]` без билдера и без
типизированного словаря** (нет `build_dcs_filter_item`/selection/order). Это ровно
режим отказа «высокая абстракция без вокабуляра → агент угадывает payload». Следствия:
- `describe(unit='dcs')` обязан перечислять под-язык настроек (не только архетипы
  компоновки и роли) — иначе `set_dcs` небезопасен на самом частом контенте.
- Параллельно в библиотеке нужны типизированные хелперы фильтра/отбора/порядка
  (совпадает с backlog `scope.md`: filter, deep grouping, hierarchy, periodAddition).
  Без них тезис «агент строит схему, покрывающую бóльшую часть функционала» не
  выполняется на каталожных схемах.

## Инвариант

> **Число write-tools не зависит от числа видов объектов и типов элементов.**

Новое — это данные (значение `kind`, запись в `describe`), не новый tool. Проверка
любого будущего изменения: если оно требует нового tool на новый вид объекта/элемента —
таксономия нарушена.

## План миграции (за развилкой, без слома движка)

> **Выполнено (commit `63270e3`).** Фактический разрез отличался от плана в одном:
> адаптерную фазу (шаги 2/5) пропустили — старые `set_report_*` / `*_project` удалены
> сразу в том же коммите (`kind`-резолвер `ConstructorTools._resolve_kind` покрыл оба
> семейства). Дубли в `shared/constructor/` сведены (`export.py`+`export_report.py`,
> `validate.py`+`validate_report.py`), `describe` добавлен. Тесты `test_constructor_facade.py`
> / `test_e2e_dispatch.py`. Прямой cutover без адаптеров допустим, т.к. у конструктора нет
> корпуса «реальных выгрузок» для A/B (в отличие от read-стороны C-MCP) и мало вызывающих.

1. Ввести новые tools (`create`/`set_object`/`set_form`/`set_dcs`/`set_template`/
   `set_module`/`validate`/`export`) поверх существующего `ConstructorTools` —
   как тонкие фасады к тем же методам `db.py`/`export*`/`validate*`.
2. Старые `set_report_*` / `*_project` оставить временно как **адаптеры** к новым
   (не удалять сразу — не ломать текущие сценарии из `mcp-tools.md`).
3. Свести дубли в `shared/constructor/`: `export.py`+`export_report.py` → один экспорт
   с ветвлением по `kind`; так же `validate.py`+`validate_report.py`.
4. Добавить `describe`.
5. После проверки на реальном диалоге (см. `testing-protocol.md`) — удалить адаптеры,
   обновить `mcp-tools.md`.

## Что НЕ меняется

- **`1c-metadata-schema`** — не трогаем, движок уже единый (`build_external_report` не
  форкнут). Таксономия — чисто про MCP-слой H-MCP.
- **`constructor.db`** — состояние проектов; схема уже несёт `kind`.
- **BSL-валидация** — эвристический `validate_code` отключён (массовый false-positive шум
  без трекинга типов); `HelpTools.validate_code` — заглушка-seam под будущий линтер.

## Открытые решения

- `validate` + `export` — два tool или один `lifecycle(action=…)`? Рекомендация: два
  (разная семантика ошибок), но это правка одной строки таблицы.
- Гранулярность `describe`: один tool с параметром `unit` vs `describe_form` /
  `describe_dcs` по отдельности. Рекомендация: один с `unit` (инвариант «tools не
  растут»).
- `set_object`: `attributes` и `tabular_sections` одним вызовом (полная замена
  оболочки) — подтвердить, что stateless-билдер это принимает разом (по
  `metadata-constructor-plan.md` — да, «билдер принимает всё разом»).

## Ссылки

- Проект конструктора и `constructor.db`: [`metadata-constructor-plan.md`](metadata-constructor-plan.md)
- Текущая поверхность tools: [`mcp-tools.md`](mcp-tools.md)
- Единый движок, неформкнутый билдер: `1c-metadata-schema/docs/scope.md`
- Парная задача на read-стороне (СКД крепится не только к отчётам):
  `1c-config-mcp/docs/dcs-schema-indexing.md`
