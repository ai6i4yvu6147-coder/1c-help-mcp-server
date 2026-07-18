# Дизайн: `describe` + хелперы под-языка настроек СКД

Детальный дизайн двух связанных вещей, вынесенных на критический путь write-стороны
проверкой на 146 реальных схемах (см. `dcs-schema-indexing.md` в C-MCP, раздел «Проверка
на реальных схемах»):

1. **`describe`** — reflection-справка конструктора (противовес высокой абстракции
   обобщённых сеттеров из [`write-tools-taxonomy.md`](write-tools-taxonomy.md)).
2. **Хелперы под-языка настроек СКД** (`build_dcs_filter_item` / `_selection_item` /
   `_order_item`) в библиотеке `1c-metadata-schema` — сейчас настройки принимаются как
   сырой `dict` без типизации, а именно они доминируют в каталожных схемах.

Эти две вещи — одно целое: `describe(unit='dcs')` **сериализует ровно словарь этих
хелперов**. Добавили хелпер/enum → `describe` обновился сам. Статус: **реализовано** —
`describe(unit='dcs')` покрывает все 12 разделов (`dataset`, `dataset_link`, `field`,
`role`, `calculated_field`, `total_field`, `parameter`, `output_parameter`, `filter`,
`selection`, `order`, `layout`); каждый привязан инвариант-тестом к сигнатуре билдера
(или к константе `DCS_FIELD_ROLE_KEYS` / объединению layout-билдеров) в
`tests/test_vocabulary.py`.

---

# Часть A. Инструмент `describe`

## Назначение и границы

`describe` отвечает на вопрос агента «**что я вообще могу передать в этот сеттер**»:
типы элементов, их поля (обязательные/опциональные), допустимые значения enum, минимальный
пример. Это **не** справка по BSL/языку запросов (она отдельно: `get_syntax`,
`get_object_api`, `get_query_syntax`) — это словарь **конструктора XML**, которого сейчас
нет вообще.

Без него обобщённый `set_form`/`set_dcs` — это «высокая абстракция без вокабуляра →
агент угадывает payload». `describe` — обязательный парный инструмент, а не украшение.

## Сигнатура

```
describe(unit: str, name: str | None = None) -> dict
```

- `unit` — крупная единица редактирования (совпадает с сеттерами таксономии):
  `object` | `form` | `dcs` | `template` | `module` | `types`.
- `name` — опциональный дриллдаун внутри единицы: конкретный тип элемента/подраздел
  (`form/InputField`, `dcs/filter`, `dcs/layout`, `types/qualifiers`). Без `name` — обзор
  единицы (список её разделов + краткое содержание).

Один tool с параметром `unit`, не `describe_form`/`describe_dcs` по отдельности — держим
инвариант «число tools не зависит от числа видов объектов и типов элементов».

## Форма ответа

Единый машинно-читаемый контракт для любого `unit/name`:

```jsonc
{
  "unit": "dcs",
  "name": "filter",                     // раздел, если запрошен
  "summary": "Элемент отбора настроек компоновки (dcsset:filter).",
  "fields": [
    {
      "name": "field",
      "required": true,
      "type": "string",
      "doc": "Путь поля (левая часть сравнения, dcscor:Field).",
      "enum": null
    },
    {
      "name": "comparison",
      "required": false,
      "type": "enum",
      "default": "Equal",
      "enum": ["Equal","NotEqual","Greater","GreaterOrEqual","Less",
               "LessOrEqual","InList","NotInList","Contains","NotContains",
               "Filled","NotFilled","BeginsWith","Like","InHierarchy"],
      "enum_confirmed": ["Equal","Contains"],   // встречено на реальных выгрузках
      "doc": "Вид сравнения (comparisonType)."
    },
    { "name": "value", "required": false, "type": "any",
      "doc": "Правая часть; тип задаётся value_type." },
    { "name": "value_type", "required": false, "type": "string",
      "doc": "xsi:type правой части: xs:string | v8:StandardBeginningDate | "
             "v8:ValueListType | cfg:CatalogRef.* | ..." },
    { "name": "use", "required": false, "type": "bool", "default": true },
    { "name": "presentation_ru", "required": false, "type": "string",
      "doc": "Заголовок отбора в пользовательских настройках." }
  ],
  "example": {
    "field": "Организация", "comparison": "Equal", "use": false
  },
  "related": ["dcs/selection", "dcs/order", "dcs/layout"]
}
```

Поля контракта: `summary`, `fields[]` (`name`/`required`/`type`/`default`/`enum`/
`enum_confirmed`/`doc`), `example`, `related[]`. Для обзора единицы (без `name`) —
`sections[]` с краткими `summary` вместо `fields`.

Два уровня детализации в одном ответе: `doc` для человека-агента, `enum`/`required`/
`type` для программной сборки payload.

## Единый источник: словарь в библиотеке, `describe` — сериализатор

`describe` **не хранит** словарь у себя (иначе он разойдётся с билдером — та же болезнь,
что таксономия лечит на уровне tools). Словарь живёт в библиотеке декларативно:

- Новый модуль `onec_metadata_schema/vocabulary.py` — структура `VOCABULARY: dict[unit ->
  dict[name -> FieldSpec...]]`, ссылающаяся на те же enum-константы, что и билдеры/
  валидатор (напр. `COMPARISON_TYPES`, `LAYOUT_MODES`, `DCS_ROLES`).
- `describe` в H-MCP — тонкий сериализатор среза `VOCABULARY[unit][name]` в контракт
  выше. Никакой ручной таблицы на стороне H-MCP.

**Инвариант авто-роста:** добавили в библиотеку `build_dcs_filter_item`/новый тип
элемента формы/enum → добавили запись в `VOCABULARY` в том же коммите → `describe`
отражает это без правок tool. Проверка PR: новый билдер без записи в `VOCABULARY` — дефект
(можно закрыть тестом «каждый публичный `build_*` представлен в `VOCABULARY`»).

## Покрытие по единицам (первый срез)

| `unit` | разделы (`name`) |
|---|---|
| `object` | `attribute`, `tabular_section` (форма `type_raw`, квалификаторы → `types`) |
| `form` | `InputField`, `LabelField`, `CheckBoxField`, `RadioButtonField`, `UsualGroup`, `Pages`/`Page`, `Table`, `Command`, `spreadsheet_field`, `event` |
| `dcs` | `dataset`, `dataset_link`, `field`, `calculated_field`, `total_field`, `parameter`, `layout` (архетипы flat/group/pivot), **`filter`**, **`selection`**, **`order`**, `role`, `output_parameter` |
| `template` | `area`, `cell` (MXL — отдельный трек, заглушка-обзор) |
| `types` | `qualifiers` (string/number/date), формы `type_raw` (`xs:*`, `cfg:*Ref.*`, `v8:*`) |

`dcs` — самый нагруженный раздел, и именно его под-язык настроек (`filter`/`selection`/
`order`) сейчас без хелперов. См. часть B.

---

# Часть B. Хелперы под-языка настроек СКД (библиотека)

## Разрыв (по реальным данным + текущему энкодеру)

Прогон на каталожных схемах (`СКД_ПравилаОтбораСобытий`, `ВыборкаДанных`, `Отборы`)
показал: доминирующий контент — `dcsset:filter`/`selection`/`order`. Текущий
`_encode_settings_variant` (`dcs.py`) принимает их как сырой `dict` и **уже реальности**:

| Что в реальном XML | Текущий энкодер | Разрыв |
|---|---|---|
| `right` типов `xs:string`, `v8:StandardBeginningDate`, `v8:ValueListType`, скаляры | `right` захардкожен: пустой `v8:ValueListType`, **только при `use=True`** | нельзя задать значение/тип правой части |
| `right` присутствует и при `use=false` (напр. `ДатаДоговора` → `StandardBeginningDate`) | при `use=false` `right` не пишется вовсе | теряется преднастроенное значение отключённого отбора |
| `userSettingPresentation` на элементе фильтра (`Владелец` → «Контрагент») | пишется только для `dataParameters`, не для фильтра | нет заголовка отбора |
| `dcsset:order` с явным `OrderItemField` + направление | только `OrderItemAuto` (внутри группировки) | нет явной сортировки по полю |
| нет типизированного входа — агент строит `dict` вслепую | — | нет вокабуляра (закрывается `describe`) |

Вывод: нужны **типизированные хелперы** + расширение энкодера, обратно совместимые с
нынешними `dict`-вызовами.

## `build_dcs_filter_item`

```python
def build_dcs_filter_item(
    field: str,                       # left, dcscor:Field
    comparison: str = 'Equal',        # comparisonType (см. enum)
    *,
    use: bool = True,
    value=None,                       # right; если None и value_type None — right опускается
    value_type: str | None = None,    # xsi:type правой части
    view_mode: str = 'Auto',          # Auto | QuickAccess | Normal | Inaccessible (dcsset:viewMode)
    presentation_ru: str | None = None,   # userSettingPresentation
    user_setting_id: str | None = None,   # выносит отбор в польз. настройки
    generate_user_setting_id: bool = False,
) -> dict: ...
```

Правило `right` (уточняет текущее хардкод-поведение, сохраняя дефолт):
- `value_type` задан → `right` c этим `xsi:type`; `value` кодируется через существующий
  `_append_value_type`/`_type_slot` (переиспуем механику параметров).
- `value_type` None, `value` None, `use=True` → **текущий дефолт**: пустой
  `v8:ValueListType` (обратная совместимость — не ломаем ФТ_ОтчетПоОстаткам_СКД).
- `value_type` None, `value` None, `use=False` → `right` опускается (текущее поведение).
- `presentation_ru` → `dcsset:userSettingPresentation` (LocalStringType) — теперь и для
  фильтра.

## `build_dcs_selection_item`

```python
def build_dcs_selection_item(field: str, *, use: bool = True) -> dict: ...
```

Строковый шорткат сохраняется (энкодер уже принимает `str`). `SelectedItemAuto`
(авто-выбор) — отдельный флаг `auto=True` без `field`. Групповой/иерархический выбор —
за рамками первого среза.

## `build_dcs_order_item` — реализовано (2026-07-18)

```python
def build_dcs_order_item(field: str | None = None, *, direction: str = 'Asc', auto: bool = False) -> dict:  # Asc | Desc
```

`OrderItemAuto` — `auto=True`. Форма `dcsset:OrderItemField` **подтверждена** на реальной
выгрузке с явной сортировкой (`ФТ_АвансыПоставщикам/ОсновнаяСхемаКомпоновкиДанных` —
top-level `<dcsset:order>` с двумя `OrderItemField`: `Списание`, `Организация`, оба `Asc`).
Энкодер эмитит явный `<dcsset:order>` на уровне настроек **между `dataParameters` и
`outputParameters`** (реальный порядок дочерних той же выгрузки); передаётся через
`order_items` у layout-билдеров. Секция `order` есть в `describe(unit='dcs', name='order')`.
Направления — `ORDER_DIRECTIONS = ('Asc', 'Desc')`. Валидатор флагует ссылку на
несуществующее поле (`settings order references unknown field`). Внутри структурных
элементов (группировки/таблицы) по-прежнему авто-`OrderItemAuto` — без регрессии.

## Значения правой части и пользовательские настройки (подтверждено на данных 2026-07-18)

Два предметных правила от пользователя, подтверждённых на реальных выгрузках
(`ТД_ОтчетПоТранспортнымСредствам/СКД`, `ТД_ОтчетГлонасс/СхемаСКД`). Оба формируют
словарь `describe` и дефолты хелперов.

### Отбор — это шаблон; значение обычно заполняет пользователь

**Важно для формулировок `describe` (чтобы не ввести агента в заблуждение).** Отбор в схеме
— это *шаблон отбора*, а не готовое условие. Отбор **по ссылочному полю нормален** (напр. по
`Организация`); левая часть — любое поле СКД. Выполняемая часть отчёта = **фиксированные
настройки схемы + пользовательские настройки поверх** (режим предприятия), и конкретную
ссылку (реальную организацию) пользователь выбирает уже при выполнении отчёта.

Дефолт для агента: **объявить, по каким полям фильтровать, и вынести их в пользовательские
настройки — конкретное значение по умолчанию НЕ зашивать** (оставить пустым). Правая часть
опционально может быть фиксированным значением: примитив, встроенная конструкция СКД
(стандартный период), предопределённое значение, или **ссылка на другое поле СКД**
(`value_type='dcscor:Field'`, подтверждено: `ОбъемГруза NotEqual` →
`<dcsset:right xsi:type="dcscor:Field"/>`). Чего не бывает на этапе конфигурирования —
конкретного непредопределённого элемента данных; но его туда и не нужно зашивать, это ровно
то, что заполняет пользователь.

Поэтому `describe` описывает **не «что в принципе бывает в шаблоне»**, а *как объявить
фильтруемое поле и вынести его пользователю*; фиксированное значение — опция, не требование.
Никакой «запрещающей» проверки в `validate()` — она только запутает (по ссылочному полю
фильтр валиден).

### Пользовательские настройки: видимость на форме (`viewMode` + `userSettingID`)

И у отборов, и у параметров есть свойства, определяющие, **отрисуется ли элемент сразу на
форме отчёта** или пользователю надо проваливаться в настройки:

- `dcsset:userSettingID` (GUID) — **включает** элемент в пользовательские настройки.
  Уже есть в `build_dcs_filter_item` (`user_setting_id`/`generate_user_setting_id`) и в
  `dataParameters` энкодера.
- `dcsset:viewMode` — режим отображения (колонка «Режим отображения» в Конфигураторе):
  `Auto` (умолчание, опускается) | `QuickAccess` (на форме, «быстрый доступ») | `Normal`
  (только в диалоге настроек) | `Inaccessible`. Подтверждено:
  `<dcsset:viewMode>Inaccessible</dcsset:viewMode>`.

Расширения:
- `build_dcs_filter_item` получает `view_mode` (по умолчанию `Auto`/опущен); энкодер
  эмитит `dcsset:viewMode` после `right`, `userSettingID` — ближе к концу элемента.
- **Дефолт-политика (agent-facing, в `describe`/`set_dcs`):** основные отборы (Организация,
  период и т.п.) по умолчанию **включать в пользовательские настройки** (`user_setting_id` +
  `viewMode='QuickAccess'`), чтобы они были сразу на форме. Порядок дочерних в элементе —
  подтвердить полным чтением реального элемента перед реализацией `view_mode`.

## Enum `comparisonType`

Платформенный `ВидСравненияКомпоновкиДанных`. В `describe` отдаём полный список +
`enum_confirmed` (встречено на данных):

- **Подтверждено на выгрузках:** `Equal`, `Contains`.
- **Платформенный набор (справочно, верифицировать при использовании):** `NotEqual`,
  `Greater`, `GreaterOrEqual`, `Less`, `LessOrEqual`, `InList`, `NotInList`,
  `InListByHierarchy`, `InHierarchy`, `NotContains`, `Filled`, `NotFilled`, `Like`,
  `NotLike`, `BeginsWith`, `NotBeginsWith`.

Enum-константа `COMPARISON_TYPES` — в библиотеке, одна на билдер/валидатор/`vocabulary`.

## Расширения энкодера `_encode_settings_variant`

- Параметризовать `right`: `value`/`value_type` (через `_append_value_type`), с правилами
  дефолта выше. **Реализовано.**
- Эмитить `dcsset:userSettingPresentation` для элементов фильтра. **Реализовано.**
- Явный `dcsset:order` с `OrderItemField` наряду с текущим `OrderItemAuto`.
  **Реализовано (2026-07-18)** — форма подтверждена на `ФТ_АвансыПоставщикам`, эмитится
  между `dataParameters` и `outputParameters`, вход через `order_items`.
- Всё за флагами присутствия ключей — **старые `dict`-вызовы дают тот же XML** (round-trip
  на текущих reference-файлах не должен измениться).

## Связь A↔B

`VOCABULARY['dcs']['filter'|'selection'|'order']` описывает ровно параметры этих хелперов
и `COMPARISON_TYPES`. Один источник: правишь хелпер/enum — правишь `VOCABULARY` — и
`describe`, и билдер, и валидатор синхронны.

---

## Грунтовка на реальном примере

Фрагмент `Catalogs/ДоговорыКонтрагентов/.../СКД_ПравилаОтбораСобытий` (реальный отбор)
должен собираться так:

```python
build_dcs_flat_layout(
    variant_name='Основной',
    selection=[
        build_dcs_selection_item('ВидДоговора'),
        build_dcs_selection_item('Владелец'),
        # ...
    ],
    filter_items=[
        build_dcs_filter_item('ВидДоговора', 'Equal', use=False),
        build_dcs_filter_item('Владелец', 'Equal', use=False,
                              presentation_ru='Контрагент'),
        build_dcs_filter_item('ДатаДоговора', 'Equal', use=False,
                              value_type='v8:StandardBeginningDate'),
        build_dcs_filter_item('НомерДоговора', 'Contains', use=False,
                              value_type='xs:string'),
    ],
)
```

Критерий: `parse(реальный файл) -> build -> serialize -> parse` даёт эквивалентную
структуру отбора (round-trip), затем — загрузка в Конфигураторе.

## Верификация

1. Round-trip на `СКД_ПравилаОтбораСобытий` (реальный каталожный отбор) — новые хелперы
   воспроизводят `filter`/`selection`.
2. Round-trip **без регрессии** на текущих reference (ФТ_ОтчетПоОстаткам_СКД, РВП) —
   старые `dict`-вызовы дают прежний XML.
3. `describe(unit='dcs', name='filter')` возвращает контракт, поля совпадают с сигнатурой
   `build_dcs_filter_item` (тест «сигнатура ↔ VOCABULARY»).
4. Живой MCP-диалог: агент строит схему с отбором, опираясь только на `describe`
   (без чтения исходников билдера) — см. `testing-protocol.md`.

## Открытые решения

- `describe`: `enum_confirmed` отдавать всегда или только по флагу? Рекомендация: всегда —
  агенту полезно знать, что проверено на данных.
- `value` правой части: принимать «сырое» значение + `value_type`, или ввести типовые
  хелперы (`dcs_value_date`, `dcs_value_list`)? Рекомендация: начать с `value`+`value_type`
  (минимум механики), типовые — по мере частотности.
- `FilterItemGroup` (И/ИЛИ-группы отборов) — за рамками первого среза; вводить, когда
  встретится реальная потребность.
- ~~Явный `OrderItemField` — только после reference-выгрузки с ним.~~ **Закрыто
  (2026-07-18)**: подтверждён на `ФТ_АвансыПоставщикам`, реализован (`build_dcs_order_item`).

## Ссылки

- Таксономия и место `describe`/`set_dcs`: [`write-tools-taxonomy.md`](write-tools-taxonomy.md)
- Проверка на 146 схемах, находка про под-язык настроек: `1c-config-mcp/docs/dcs-schema-indexing.md`
- Текущий билдер/энкодер СКД: `1c-metadata-schema/src/onec_metadata_schema/dcs.py`
  (`_encode_settings_variant`, `build_dcs_*layout`)
- Backlog библиотеки (filter, deep grouping, hierarchy, periodAddition):
  `1c-metadata-schema/docs/scope.md`
