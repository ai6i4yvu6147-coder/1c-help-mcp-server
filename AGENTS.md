## Agent hints

**Role:** Sub (subordinate) · group `1c-cursor` · Head: `1c-admin-tool` (`C:/projects/1c-admin-tool`).

**Subagent:** `.cursor/agents/` — **1** (`doc-librarian`). **Skills:** `.cursor/skills/` — **4** (`normalize-project`, `canon-align`, `maintain-docs`, `sync`).

Full context is in `docs/`:

1. `docs/agent-map.md` — entry: policies, directory map, hub triggers
2. `docs/todo.md` — backlog; check `## Hub pending`
3. `docs/architecture.md` — data flow, components, product policies
4. `docs/README.md` — index and domain specs
5. `docs/group/integration.md` — Head link and protocol state

Before a session: if `docs/todo.md` has `## Hub pending` — skill **`sync`**.

On DB schema or import format changes — recreate databases via Admin (see `.cursor/rules/no-db-migrations.mdc`).

Structure check: `python scripts/project-doctor.py --repo . --type Sub`.
