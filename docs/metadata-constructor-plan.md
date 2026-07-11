# План: конструктор метаданных (внешние обработки → расширения)

Зафиксировано по итогам обсуждения 2026-07-11; обновлено после готовности библиотеки (Stage C–D, Configurator load подтверждён). Направление — **Stage E**, готово к реализации.

## Идея

Помимо справки/валидации BSL-синтаксиса (уже реализовано: `get_syntax`, `search_syntax`, `get_object_api`, `validate_code`), проект расширяется вторым назначением: конструктор корректных 1C-артефактов. Сначала — внешние обработки, затем — расширения конфигурации.

Модель работы: агент работает с «проектом» в БД сервера (`constructor.db`: create → attributes → form → module code → validate → export). Сервер управляет GUID/ItemID/перекрёстными ссылками через библиотеку `1c-metadata-schema` (stateless builder).

## Зависимость: 1c-metadata-schema

XML-знание не дублируется здесь — библиотека `C:/projects/1c-metadata-schema` (`pip install -e`, импорт `onec_metadata_schema`). Stages C–D **готовы** (Configurator load подтверждён дважды). Кластерный канон: Head `docs/group/shared/metadata-library-cluster.md`.

Актуальный API билдера (см. demo-скрипты `scripts/build_test_poryadka_demo.py`, `scripts/build_reperfill_demo.py` в том репозитории):

```python
from onec_metadata_schema import serialize, validate
from onec_metadata_schema.builder import (
    build_external_data_processor,   # name, synonym_ru, attributes=[...], form_name=...
    build_form_descriptor,           # form_name, synonym
    build_form_layout,               # object_type_raw, fields=[], groups=[], commands=[], events=?
)
```

Билдер — чистые функции без состояния: каждый вызов пересчитывает id/GUID из полного переданного списка.

## Место в кластере (`1c-cursor`)

- `1c-config-mcp` — read-only индексатор; отдельный трек «внешняя обработка как третий вид корня» (не блокирует конструктор).
- `1c-help-mcp` (этот проект) — BSL/язык запросов + конструктор XML (Stage E).
- `1c-data-mcp` — v6 execution: валидация BSL перед исполнением — через этот проект, не локальный чекер.

## Подсистема `shared/constructor/`

Отдельно от `help_parser.py` / `query_parser.py` / `db_manager.py`. Своя SQLite `constructor.db`:

- `processor` (name, synonym)
- атрибуты формы/объекта — JSON-документ на форму или нормализованные таблицы (на выбор при реализации; билдер принимает всё разом)
- тексты модулей (`ObjectModule`, `Forms/.../Module.bsl`) — как текст

## MCP tools (Stage E)

| Tool | Действие |
|---|---|
| `create_processor(name, synonym)` | создаёт проект |
| `set_attributes(processor, [{name, type_raw, qualifiers?}, ...])` | объектные реквизиты |
| `set_form(processor, fields=[], groups=[], table=?, commands=[], events=?)` | параметры 1:1 с `build_form_layout` |
| `set_module_code(processor, module, code)` | тело модуля |
| `validate_project(processor)` | (1) `validate()` библиотеки над деревьями; (2) `validate_code`/`get_object_api` над BSL; (3) у каждого `Event`/`Command.Action` в спеке формы есть процедура в сохранённом модуле |
| `export_project(processor, path)` | `build_*` + `serialize()` → 3-файловое дерево + модули |

Регистрация — по образцу `server/server.py` / `server/tools.py`.

## Критерий готовности Stage E

Первый **E2E через реальный диалог с агентом** (не Python demo-скрипт): воспроизвести `обр ТестПорядка` или проще → вручную открыть в Конфигураторе.

## Открытые вопросы (не блокируют старт)

- Заглушки обработчиков формы (`ПриИзменении`/`ПриОткрытии`) в MVP — по факту использования.
- `TabularSection` на уровне объекта, шаблон `СведенияОВнешнейОбработке()` — подключать только если конкретная обработка упрётся.

## Дальше

- Расширение охвата элементов формы по запросу библиотеки.
- Расширения конфигурации (Extension) — Stage G в `1c-metadata-schema`, отдельный крупный этап после стабилизации MVP.
