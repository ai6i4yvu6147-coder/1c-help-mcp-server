# Group integration

## Head project

- **group id:** `1c-cursor`
- **head id:** `1c-admin-tool`
- **path:** `C:/projects/1c-admin-tool`
- **protocol canon:** `C:/projects/1c-admin-tool/docs/group/shared/`
- **group map (Head):** `C:/projects/1c-admin-tool/docs/group/README.md`

## Protocol state

| Field | Value |
|-------|-------|
| protocol_epoch | 0 |
| protocol_sync_state | stable |
| stable_at | 2026-06-30T06:49:49Z |
| protocol_ref | `docs/group/protocol-ref/epoch0/` |
| last_offer_from_head | `20260630T064821-1c-admin-tool` (snapshot `protocol-snapshot-epoch0-20260630T064821`) |
| open_disputes | 0 |
| disputes_resolved | 0 |
| dispute_round | 0 |

`protocol_sync_state`: `negotiating` | `stable` | `stale`

## Sync (packets)

- **inbox:** `docs/group/inbox/` — packets from Head (gitignored; process and delete)
- **outbox:** `docs/group/outbox/` — packets for Head (after skill **`sync`**)
- **operator:** copy between repos — [`OPERATOR-HANDOFF.md`](OPERATOR-HANDOFF.md)
- **protocol-ref:** `docs/group/protocol-ref/epoch<N>/` — fixed Head baseline (commit)
- **packet templates:** `docs/group/templates/`

Before work: skill **`sync`** (when the operator reports inbox is ready).

## Sync versions (deltas after stable)

| Field | Value |
|-------|-------|
| last_sync_from_head | |
| last_sync_to_head | |

## Local deviations

- **Portable MCP runtime:** autonomous; help and tools work without the Hub.
- **protocol-ref:** `docs/group/protocol-ref/epoch0/` — Head baseline (epoch 0, v1.0.3); Hub/MCP group canon.
- **Help domain:** HBK import, SQLite, parsers — local specs in `docs/`; not Hub group canon, no dispute.

## Status

| Area | Status | Note |
|------|--------|------|
| Hub / group integration | stable | epoch 0 accepted; baseline v1.0.3 in protocol-ref |
| Managed tool registry | — | After protocol stable |
| Portable MCP runtime | autonomous | Does not depend on Hub for help operation |
