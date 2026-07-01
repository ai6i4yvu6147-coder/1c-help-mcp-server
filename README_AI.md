## AI context

> **Note:** Agent-cache documentation is in **English** — start with `docs/agent-onboarding.md`. This file is a brief Russian pointer; domain specs (`mcp-tools.md`, `database.md`, `testing-protocol.md`) remain in Russian.

Full project documentation and rules — in `docs/`.

**Role:** Sub (module `1c-help-mcp`, group `1c-cursor`, Head `1c-admin-tool`).

**Subagent:** `doc-librarian` (`.cursor/agents/`). **Skills:** 4 in `.cursor/skills/` — `normalize-project`, `canon-align`, `maintain-docs`, `sync`.

### Start here

1. `docs/agent-onboarding.md`
2. `docs/todo.md` (including `docs/group/inbox/` check)
3. `docs/architecture.md`
4. `docs/README.md` (index and domain specs)
5. `docs/group/integration.md` (Head link)

### Key rules

- **NO_DB_MIGRATIONS**: no SQLite migrations — databases are recreated via Admin.
- **Testing**: only via MCP tools on a connected server (see `docs/testing-protocol.md`).
- **Group-sync**: do not commit sync packets; shared protocol canon — in Head `docs/group/shared/`; packet delivery — operator per `docs/group/OPERATOR-HANDOFF.md`, processing — skill `sync`.
