# Отчёт о нормализации: 1c-help-mcp

**Дата:** 2026-06-30  
**Роль:** Sub (subordinate)  
**Канон:** 2.2.0 (Workspace improve)  
**Метод:** agent-first (без `normalize-apply.py`)

---

## Идентификаторы

| Поле | Значение |
|------|----------|
| Модуль (sub id) | `1c-help-mcp` |
| Группа | `1c-cursor` |
| Head | `1c-admin-tool` |
| Путь к Head | `C:/projects/1c-admin-tool` |
| Состояние протокола | `negotiating`, epoch 0 |

Head в этом заходе **не изменялся** — только зафиксирован в manifest и docs.

---

## Что сделано

### Структура (канон Sub)

| Артефакт | Статус |
|----------|--------|
| `group.manifest.yaml` | Создан, заполнен |
| `docs/group/integration.md` | Создан, заполнен |
| `docs/group/inbox/`, `outbox/` | Созданы (gitignored) |
| `docs/canons/` | Локальная копия WI (6 файлов) |
| `docs/todo.md` | Создан |
| `docs/normalize-record.md` | Создан |
| `tests/` | Зарезервирован (`.gitkeep`) |
| `scripts/` | `project-doctor`, `sync-relay`, `sync-status`, `protocol-snapshot` |
| `.cursor/skills/` | 9 skills |
| `.cursor/agents/` | 4 agents |
| `.cursor/rules/no-db-migrations.md` | Сохранён |

### Корень

| Действие | Детали |
|----------|--------|
| `readme.txt` → `README.md` | Миграция по канону |
| Удалены | `anketa_*`, `unified-admin-protocol*` (черновики) |
| `requirements.txt` | Добавлен `pyyaml>=6.0`; `mcp`, `beautifulsoup4`, `lxml`, `pyinstaller` **сохранены** |
| `.gitignore` | `plans/`, `scratch/`, `docs/group/inbox|outbox|.arbitration/` |

### Документация (приведение к канону)

Обновлены по `docs/canons/documentation.md`:

| Файл | Изменение |
|------|-----------|
| `AGENTS.md` | Роль Sub, порядок чтения, inbox, project-doctor |
| `docs/agent-onboarding.md` | Тип Sub, group-sync политики, каноны, ссылки |
| `docs/README.md` | Порядок чтения канона, оглавление, group-sync |
| `docs/architecture.md` | Секция «Позиция в группе» |
| `README_AI.md` | Роль Sub, group-sync правила |
| `docs/canons/README.md` | Пути артефактов этого репо (не WI) |
| `CHANGELOG.md` | Запись 2026-06-30 |

**Не изменялись:** `docs/mcp-tools.md`, `docs/database.md`, `docs/testing-protocol.md` (доменные спеки актуальны).

### Не создано (по канону — позже)

- `docs/group/protocol-ref/epoch<N>/` — после `protocol_offer` и reconcile
- Hooks (`.cursor/hooks/`) — опционально, не требовались для Sub
- Каталог `templates/` в продуктовом репо — не создавался

---

## Проверка

```text
python scripts/project-doctor.py --repo . --type Sub
→ OK (0 warning(s))
```

---

## Продуктовый код

`server/`, `admin_tool/`, `shared/` — **без изменений**. Portable MCP остаётся автономным.

---

## Следующие шаги

1. Нормализовать Head (`1c-admin-tool`) как H — разместить канон в `docs/group/shared/`.
2. Получить `protocol_offer` от Head или запустить `run-protocol-reconciliation`.
3. После `stable` — синхронизация managed-tool контракта с Hub; при критичных изменениях — `emit-group-sync-packet` + `sync-relay.py --deliver`.

---

## Инциденты и обратная связь

### 1. Непредвиденный normalize (`--upgrade-wi`)

Ранее (тот же день) проект подвергся **непредвиденному** normalize с `--upgrade-wi`, что перезаписало `requirements.txt`. Последствия откачены; повторная нормализация выполнена вручную по initiator `subordinate.md` с сохранением продуктовых зависимостей.

### 2. Обход doc-librarian при правке документации

**Что случилось:** после нормализации структуры родительский агент сам отредактировал `AGENTS.md`, `docs/agent-onboarding.md`, `docs/README.md`, `docs/architecture.md`, `README_AI.md`, `CHANGELOG.md` и создал `normalize-report.md` — **без делегирования** субагенту `doc-librarian`, хотя skill `maintain-docs` прямо требует:

> Invoke subagent **doc-librarian** … Do not perform large doc edits in the parent chat.

**Почему это проблема:** в репозитории materialized роль doc-librarian именно для ведения docs Sub; обход skill ломает задуманный процесс group-sync и размывает ответственность за согласованность entry points.

**Исправление:**

1. Запущен **doc-librarian** (ревью документации) — вердикт **pass-with-fixes**.
2. Применены обязательные правки:
   - `AGENTS.md`, `README_AI.md` — порядок чтения по канону (добавлен `architecture.md`)
   - `docs/todo.md` — явная проверка `docs/group/inbox/`
   - `docs/group/integration.md` — ссылка на карту группы Head (`docs/group/README.md`)
   - `docs/README.md` — дополнительные CLI (`sync-status`, `protocol-snapshot`), skill `process-group-inbox`
   - `docs/canons/README.md` — примечание о версиях канонов
   - `CHANGELOG.md` — уточнён список затронутых файлов

**Урок для WI / агентов:** при запросе «привести docs в соответствие с каноном» после normalize — сначала `maintain-docs` → doc-librarian, не правки в родительском чате.

---

## Re-normalize 2.2.1

**Дата:** 2026-06-30  
**Источник:** initiator `subordinate.md` (Workspace improve)  
**Канон:** layout субагентов **2.2.1** (базовый WI canon 2.2.0)

### Дельта

| Изменение | Было | Стало |
|-----------|------|-------|
| `.cursor/agents/` | 4 agents (в т.ч. stub `canon-align`, `group-inbox-processor`) | **2 agents:** `doc-librarian`, `group-sync-arbitrator` |
| `.cursor/skills/` | 9 skills | 9 skills (без изменения числа; `canon-align`, `process-group-inbox` — **только skills**) |
| Каноны | `normalize-governance` 1.1.x, `group-sync` без таблицы 2 agents | `normalize-governance` **1.2.0** (doc-librarian обязателен), `group-sync` — таблица 2 agents |
| `.gitignore` | `docs/group/.arbitration/` в ignore | `.arbitration/` **убран** из gitignore |

### Документация (doc-librarian)

Entry-point docs приведены к канону `documentation.md` и layout 2.2.1 субагентом **doc-librarian**:

- `AGENTS.md` — 2 agents + 9 skills
- `README_AI.md` — 2 agents + 9 skills
- `docs/agent-onboarding.md` — таблица `.cursor/`, canon 2.2.1
- `docs/README.md` — секция субагентов/skills
- `CHANGELOG.md` — запись re-normalize 2.2.1
- `normalize-report.md` — этот раздел

**Примечание:** первая нормализация (см. выше) обошла doc-librarian при правке docs; в этом цикле исправлено — docs pass выполнен через `maintain-docs` → doc-librarian.

### Проверка

```text
python scripts/project-doctor.py --repo . --type Sub
→ OK (0 warning(s))
```

---

## Re-normalize 2.3.0

**Дата:** 2026-07-01  
**Источник:** initiator `subordinate.md` (Workspace improve)  
**Канон:** WI **2.3.0** (operator handoff, unified skill `sync`)

### Дельта

| Изменение | Было | Стало |
|-----------|------|-------|
| `.cursor/agents/` | 2 agents (`doc-librarian`, `group-sync-arbitrator`) | **1 agent:** `doc-librarian` |
| `.cursor/skills/` | 9 skills (в т.ч. 7 legacy group-sync) | **4 skills:** `normalize-project`, `canon-align`, `maintain-docs`, `sync` |
| Доставка пакетов | `scripts/sync-relay.py` | **Удалён** — оператор копирует outbox→inbox по `docs/group/OPERATOR-HANDOFF.md` |
| Group-sync docs | — | `docs/group/OPERATOR-HANDOFF.md`, `docs/group/templates/` |
| Состояние протокола | `stable`, epoch 0 | **Без изменений** (`integration.md`, `protocol-ref/epoch0/` сохранены) |

### Документация (doc-librarian)

Entry-point docs приведены к канону 2.3.0 субагентом **doc-librarian**:

- `AGENTS.md` — 1 agent + 4 skills, operator handoff
- `README_AI.md` — 1 agent + 4 skills, `sync` + OPERATOR-HANDOFF
- `docs/agent-onboarding.md` — таблица `.cursor/`, canon 2.3.0, operator handoff
- `docs/README.md` — секция субагента/skills, CLI без sync-relay
- `docs/todo.md` — layout 2.3.0, skill `sync`
- `CHANGELOG.md` — запись re-normalize 2.3.0
- `normalize-report.md` — этот раздел

**Не изменялись:** `docs/group/integration.md` (protocol state), `docs/mcp-tools.md`, `docs/database.md`, `docs/testing-protocol.md`.

### Проверка

```text
python scripts/project-doctor.py --repo . --type Sub
→ OK (0 warning(s))
```

---

## Re-normalize 2.4.0

**Дата:** 2026-07-02  
**Источник:** initiator `subordinate.md` (Workspace improve)  
**Канон:** WI **2.4.0** (agent-cache English, deprecations registry)

### Removed (deprecations)

Пути из блоков `2.2.0` / `2.3.0` в `<WI>/normalize.deprecations.yaml` (роль Sub: `all` + `subordinate`):

| Путь | Статус |
|------|--------|
| `scripts/sync-docs.py` | (already absent) |
| `scripts/normalize-apply.py` | (already absent) |
| `scripts/sync-relay.py` | (already absent) |
| `.cursor/agents/group-sync-arbitrator.md` | (already absent) |
| `.cursor/skills/emit-group-sync-packet/` | (already absent) |
| `.cursor/skills/process-group-inbox/` | (already absent) |
| `.cursor/skills/export-group-protocol/` | (already absent) |
| `.cursor/skills/import-group-protocol/` | (already absent) |
| `.cursor/skills/run-protocol-reconciliation/` | (already absent) |
| `.cursor/skills/review-protocol-diff/` | (already absent) |

Блок `2.3.0` / `head`: `.cursor/skills/arbitrate-protocol-dispute/` — не применимо (Sub).

### Language migration (agent-cache → English)

| Файл | Действие |
|------|----------|
| `README.md` | Перевод на английский |
| `AGENTS.md` | Перевод на английский |
| `docs/README.md` | Перевод; canon 2.4.0 |
| `docs/agent-onboarding.md` | Перевод; canon 2.4.0 |
| `docs/architecture.md` | Перевод на английский |
| `docs/todo.md` | Перевод; canon 2.4.0 |
| `docs/group/integration.md` | Перевод; protocol state сохранён |
| `docs/canons/README.md` | Секция «Artifacts in this repository» |

**Не переводились:** `CHANGELOG.md`, `docs/group/OPERATOR-HANDOFF.md`, `docs/mcp-tools.md`, `docs/database.md`, `docs/testing-protocol.md`, `docs/group/protocol-ref/**`, `README_AI.md` (краткая ссылка на English docs).

### Документация (doc-librarian)

Entry-point docs переведены на английский (canon 2.4.0):

- `README.md`, `AGENTS.md`
- `docs/README.md`, `docs/agent-onboarding.md`, `docs/architecture.md`, `docs/todo.md`
- `docs/group/integration.md` (protocol state сохранён)
- `docs/canons/README.md` — «Artifacts in this repository»
- `README_AI.md` — краткая ссылка на English docs
- `CHANGELOG.md` — запись re-normalize 2.4.0 (RU)
- `normalize-report.md` — этот раздел

**Без изменений:** состояние протокола (`stable`, epoch 0, `protocol-ref`, `last_offer_from_head`, local deviations).

### Проверка

```text
python scripts/project-doctor.py --repo . --type Sub
→ OK (0 warning(s))
```
