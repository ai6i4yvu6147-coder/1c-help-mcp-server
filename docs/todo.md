# TODO

## Admin Hub / group integration

- **Status:** `stable`, epoch 0 (see [`group/integration.md`](group/integration.md))
- **Layout 2.4.0:** 1 subagent (`.cursor/agents/`: `doc-librarian`); 4 skills — `normalize-project`, `canon-align`, `maintain-docs`, `sync`
- **Inbox:** before each session check `docs/group/inbox/`; if packets present — skill **`sync`** (outbox→inbox delivery — [`group/OPERATOR-HANDOFF.md`](group/OPERATOR-HANDOFF.md)); delete after processing
- After `stable` — sync managed-tool contract with Hub when needed

## Product

- Support current 1C help versions via Admin
- Keep MCP tools documentation (`docs/mcp-tools.md`) up to date
- Testing per [`testing-protocol.md`](testing-protocol.md)

## Tech debt

- No automated unit tests (`tests/` reserved for future use)
