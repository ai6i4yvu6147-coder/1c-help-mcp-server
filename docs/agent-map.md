# Agent map

Single entry point for the orchestrator (the main agent).

## Type

**Sub (subordinate)** — module `1c-help-mcp` in group `1c-cursor`. Head: `1c-admin-tool` @ `C:/projects/1c-admin-tool` · `C:/repo/1c-config-admin-tool`.

## What this project is

Indexes unpacked 1C platform help (`shcntx_ru`, `shlang_ru`, `shquery_ru`) into SQLite and exposes MCP tools for BSL syntax assistance, query language, and heuristic code validation. The portable MCP server is **autonomous**: help and tools work without the Hub.

## Session start

1. Read `docs/todo.md`.
2. If `## Hub pending` has items → invoke skill **`sync`** before other work.
3. Full `docs/canons/` is read on normalize or dispute, not every session.

## Key policies

- **NO_DB_MIGRATIONS**: never write migrations for SQLite in `databases/` — recreate via Admin after schema/import changes (see `.cursor/rules/no-db-migrations.mdc`).
- **Testing**: verify only via MCP tool calls on a connected server; start with `list_help_versions` (see `docs/testing-protocol.md`). No direct SQLite reads or Python workaround scripts.
- **Sources vs runtime**: repo sources must not contain runtime DBs (`databases/*.db`); databases live in portable `../1c_help_mcp_server_Portable/databases/`. Agent changes sources; user rebuilds portable and reconnects MCP.
- **Parser**: when extending `shared/help_parser.py` / `shared/query_parser.py`, inspect real HTML from unpacked help (outside the repo).
- **BSL vs query language**: built-in language — `get_syntax`, `search_syntax`; query text — `get_query_syntax`, `search_query`, `list_query_topics`.
- **Group sync**: shared protocol canon lives on Head at `docs/group/shared/`; Sub reads it at `head.path` (no local copy) and updates via hub threads (skill **`sync`**).

## Directory map

```
admin_tool/               # Admin GUI (import help → SQLite)
server/                   # MCP server
shared/                   # parser, db_manager, version_resolver
docs/
  agent-map.md            # this file
  architecture.md
  todo.md
  mcp-tools.md            # MCP tools reference
  database.md             # SQLite schema
  testing-protocol.md
  group/integration.md
.tasks/                   # subagent handoff artifacts (gitignored)
```

## Subagents — when to delegate

| Agent | Delegate when | Skip when |
|-------|---------------|-----------|
| `doc-librarian` | Bulk doc edits (via `maintain-docs`) | Single typo |

Dev pipeline agents are **not** installed — this repo does not qualify as a large product repo per `dev-pipeline.md` (no test suite; focused MCP server).

Built-in **Explore** / **Bash** handle tiny queries directly.

## Orchestrator owns the loop

For multi-file work without dev agents, the orchestrator implements directly. On verification failures, cap fix loops at 3 rounds, then surface to the user.

## Test / build

```powershell
build_all.bat                                          # → ../1c_help_mcp_server_Portable/
python scripts/project-doctor.py --repo . --type Sub
python scripts/sync-status.py --repo .
```

Functional verification: rebuild portable, reconnect MCP in the IDE, call tools per `docs/testing-protocol.md`.

## Hub

- **Hub:** `C:/projects/1c-admin-tool/GROUP-HUB.md` · `C:/repo/1c-config-admin-tool/GROUP-HUB.md`
- **Sub id:** `1c-help-mcp` — edit only own registry row and threads

Sync triggers → skill `sync`: `## Hub pending` in todo, user `/sync 1c-help-mcp <topic>`, registry `stale`, or group-critical edit in Head `docs/group/shared/`.
