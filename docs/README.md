## Project documentation

Structured context for AI agents and developers. Root overview: [`../README.md`](../README.md).

**Role:** Sub · group `1c-cursor` · Head `1c-admin-tool`.

### Reading order (canon `canons/documentation.md`)

1. [`agent-onboarding.md`](agent-onboarding.md) — project type, policies, group-sync
2. [`todo.md`](todo.md) — backlog; **check unprocessed packets in** `group/inbox/`
3. [`architecture.md`](architecture.md) — data flow and components
4. Domain specs (below)
5. [`group/integration.md`](group/integration.md) — Head link and protocol state

### Domain specs

| Document | Content |
|----------|---------|
| [`mcp-tools.md`](mcp-tools.md) | MCP tools and call examples |
| [`database.md`](database.md) | SQLite schema, no-migrations policy |
| [`testing-protocol.md`](testing-protocol.md) | Verification on a connected MCP |

### Group and normalization

| Document | Content |
|----------|---------|
| [`group/integration.md`](group/integration.md) | Head, protocol state, inbox/outbox |
| [`group/OPERATOR-HANDOFF.md`](group/OPERATOR-HANDOFF.md) | Manual packet delivery between repos |
| [`group/templates/`](group/templates/) | Sync packet templates |
| [`canons/`](canons/) | Local WI canon copy |
| [`normalize-record.md`](normalize-record.md) | Last normalize metadata |

**Subagent and skills (canon 2.4.0):** `.cursor/agents/` — 1 (`doc-librarian`); `.cursor/skills/` — 4 (`normalize-project`, `canon-align`, `maintain-docs`, `sync`).

### Group-sync CLI

```powershell
python scripts/project-doctor.py --type Sub
python scripts/sync-status.py --repo .
python scripts/protocol-snapshot.py --status --repo .
```

Sync packets in `group/inbox/` and `group/outbox/` are ephemeral (in `.gitignore`); delivery — operator per [`group/OPERATOR-HANDOFF.md`](group/OPERATOR-HANDOFF.md); processing — skill **`sync`**; delete after processing.
