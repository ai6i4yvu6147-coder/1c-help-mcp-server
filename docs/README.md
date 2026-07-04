## Project documentation

Structured context for AI agents and developers. Root overview: [`../README.md`](../README.md).

**Role:** Sub · group `1c-cursor` · Head `1c-admin-tool`.

### Reading order (canon `canons/documentation.md`)

1. [`agent-map.md`](agent-map.md) — entry: type, policies, directory map, hub triggers
2. [`todo.md`](todo.md) — backlog; **check `## Hub pending`**
3. [`architecture.md`](architecture.md) — data flow, components, product policies
4. Domain specs (indexed from `architecture.md`)
5. [`group/integration.md`](group/integration.md) — Head link and protocol state

### Group and normalization

| Document | Content |
|----------|---------|
| [`group/integration.md`](group/integration.md) | Head hub link, protocol state |
| [`group/OPERATOR-HANDOFF.md`](group/OPERATOR-HANDOFF.md) | Deploy runbook (human-tier) |
| [`group/protocol-ref/`](group/protocol-ref/) | Fixed Head baseline snapshots |
| [`canons/`](canons/) | Local WI canon copy |
| [`normalize-record.md`](normalize-record.md) | Last normalize metadata |

**Subagent and skills (canon 2.5.0):** `.cursor/agents/` — 1 (`doc-librarian`); `.cursor/skills/` — 4 (`normalize-project`, `canon-align`, `maintain-docs`, `sync`).

### Group-sync CLI

```powershell
python scripts/project-doctor.py --repo . --type Sub
python scripts/sync-status.py --repo .
python scripts/protocol-snapshot.py --status --repo .
```

Hub state: `C:/projects/1c-admin-tool/GROUP-HUB.md`. Processing — skill **`sync`** when `## Hub pending` has items.
