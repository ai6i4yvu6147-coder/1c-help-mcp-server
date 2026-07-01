## Agent hints

**Role:** Sub (subordinate) · group `1c-cursor` · Head: `1c-admin-tool` (`C:/projects/1c-admin-tool`).

**Subagent:** `.cursor/agents/` — **1** (`doc-librarian`). **Skills:** `.cursor/skills/` — **4** (`normalize-project`, `canon-align`, `maintain-docs`, `sync`).

Full context is in `docs/`:

1. `docs/agent-onboarding.md` — policies and project type
2. `docs/todo.md` — backlog and unprocessed inbox packets
3. `docs/architecture.md` — data flow and components
4. `docs/README.md` — index and domain specs
5. `docs/group/integration.md` — Head link and protocol state

Before a session: if the operator reports packets in `docs/group/inbox/` — skill **`sync`** (outbox→inbox delivery is manual; see `docs/group/OPERATOR-HANDOFF.md`).

On DB schema or import format changes — recreate databases via Admin (see `.cursor/rules/no-db-migrations.md`).

Structure check: `python scripts/project-doctor.py --type Sub`.
