# Group integration

## Head project

- **group id:** `1c-cursor`
- **head id:** `1c-admin-tool`
- **hub:** `C:/projects/1c-admin-tool/GROUP-HUB.md` · `C:/repo/1c-config-admin-tool/GROUP-HUB.md`

## Protocol state

| Field | Value |
|-------|-------|
| protocol_epoch | 0 |
| protocol_sync_state | stable |
| stable_at | 2026-07-02T15:33:11Z |
| protocol_ref | `docs/group/protocol-ref/epoch0/` |
| open_disputes | 0 |
| dispute_round | 0 |

`protocol_sync_state`: `negotiating` | `stable` | `stale`

## Sync (hub)

State lives in the Head hub (`head.paths` in `group.manifest.yaml`): `C:/projects/1c-admin-tool/GROUP-HUB.md` · `C:/repo/1c-config-admin-tool/GROUP-HUB.md`. This project edits only its own `sub_id` registry row and threads.

Session start: if `docs/todo.md` has `## Hub pending`, run skill **`sync`**.

## Local deviations

- **Portable MCP runtime:** autonomous; help and tools work without the Hub.
- **protocol-ref:** `docs/group/protocol-ref/epoch0/` — Head baseline (epoch 0, v1.0.6); Hub/MCP group canon.
- **Help domain:** HBK import, SQLite, parsers — local specs in `docs/`; not Hub group canon, no dispute.

## Status

| Area | Status | Note |
|------|--------|------|
| Hub / group integration | stable | epoch 0; baseline v1.0.6 in protocol-ref (ack THR-003) |
| Managed tool registry | — | After protocol stable |
| Portable MCP runtime | autonomous | Does not depend on Hub for help operation |
