# Group integration

## Head project

- **group id:** `1c-cursor`
- **head id:** `1c-admin-tool`
- **hub:** `C:/projects/1c-admin-tool/GROUP-HUB.md`
- **shared canon:** `C:/projects/1c-admin-tool/docs/group/shared/` (read directly, no local copy)

## Sync state

| Field | Value |
|-------|-------|
| sync_state | stable |
| last_event | 20260711T053100Z |

Mirrors this Sub's `GROUP-HUB.md` registry row — the hub is the source of truth; this is a local read-cache, not a pinned protocol version.

## Sync (hub)

State lives in the Head hub at `C:/projects/1c-admin-tool/GROUP-HUB.md`. This project edits only its own `sub_id` registry row and threads.

Session start: if `docs/todo.md` has `## Hub pending`, run skill **`sync`**.

## Local deviations

- **Portable MCP runtime:** autonomous; help and tools work without the Hub.
- **Help domain:** HBK import, SQLite, parsers — local specs in `docs/`; not Hub group canon, no dispute.

## Status

| Area | Status | Note |
|------|--------|------|
| Hub / group integration | stable | Reads `shared/` at head.path directly (canon 2.6.0) |
| Managed tool registry | — | After protocol stable |
| Portable MCP runtime | autonomous | Does not depend on Hub for help operation |
