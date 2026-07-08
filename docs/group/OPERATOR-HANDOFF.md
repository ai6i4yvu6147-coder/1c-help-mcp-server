# Operator handoff — учётные данные и деплой

Human-tier — русский OK. В хаб-модели (canon 2.5.0) синхронизация протокола идёт через `GROUP-HUB.md` — оператор **не копирует пакеты** между репозиториями. За оператором остаются вещи вне контекста агента: деплой portable MCP.

---

## Репозитории группы

| Роль | Репозиторий | Путь |
|------|-------------|------|
| Head | `1c-admin-tool` / `1c-config-admin-tool` | `C:/projects/1c-admin-tool` · `C:/repo/1c-config-admin-tool` |
| Sub `1c-help-mcp` | `1c-help-mcp` / `1c-help-mcp-server` | `C:/projects/1c-help-mcp` · `C:/repo/1c-help-mcp-server` |

Хаб: `C:/projects/1c-admin-tool/GROUP-HUB.md` · `C:/repo/1c-config-admin-tool/GROUP-HUB.md`. Sub resolves via `head.paths` в `group.manifest.yaml`.

---

## Деплой portable MCP

| Шаг | Команда / действие | Ответственный |
|-----|--------------------|---------------|
| Сборка | `build_all.bat` → `../1c_help_mcp_server_Portable/` | оператор |
| Импорт справки | `Admin.bat` → «Add help» → папка с `shcntx_ru`, `shlang_ru`, `shquery_ru` | оператор |
| MCP в IDE | `command` в конфиге клиента → `Server\1c-help-server.exe` | оператор |

Агент меняет исходники; оператор пересобирает portable и переподключает MCP для проверки.

---

## Подсказка

```powershell
python scripts/sync-status.py --repo .
```
