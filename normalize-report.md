# Normalize report — 2026-07-12

**Role:** Sub · **Target canon:** 2.6.0 · **Local was:** 2.5.0

## Summary

Re-normalized `1c-help-mcp` to WI canon 2.6.0. Head (`1c-admin-tool`) already on hub 2.6 (`GROUP-HUB.md` without epoch columns). Sub migrated from pinned `protocol-ref/` snapshots to direct reads of Head `docs/group/shared/` at `head.path`.

## Removed (deprecations)

| Path | Result |
|------|--------|
| `scripts/protocol-snapshot.py` | removed |
| `docs/group/protocol-ref/` | removed (epoch0 — protocol files matched Head `shared/`; README/SNAPSHOT.yaml were snapshot metadata only) |

Blocks ≤2.5.0 paths were already absent from prior normalizes.

## Materialized from WI

| Area | Action |
|------|--------|
| `docs/canons/` | refreshed (8 files, English) |
| `group.manifest.yaml` | `canon_version: 2.6.0` |
| `docs/group/integration.md` | re-templated — `sync_state` / `last_event` (no epoch/dispute_round) |
| `.cursor/agents/doc-librarian.md` | copied |
| `.cursor/skills/` | normalize-project, canon-align, maintain-docs, sync |
| `.cursor/commands/re-normalize.md` | copied (Sub template) |
| `.cursor/rules/` | docs-in-english, keep-repo-current, prompt-authoring |
| `scripts/sync-status.py` | updated (2.6 fields) |
| `scripts/project-doctor.py` | updated (2.6 checks) |

## Docs (doc-librarian)

- `docs/agent-map.md`, `docs/README.md`, `docs/architecture.md` — hub 2.6 model, no protocol-ref/snapshot
- `docs/group/OPERATOR-HANDOFF.md` — intro refreshed; deploy table preserved
- `CHANGELOG.md` — re-normalize entry added

## Unchanged

- **Layout:** 1 agent + 4 skills (dev pipeline skipped — no test suite)
- **Sync state:** `stable`, `last_event: 20260711T053100Z`
- **Local deviations:** portable MCP runtime autonomous; help domain local specs
- **Project-local rule:** `.cursor/rules/no-db-migrations.mdc`

## Checks

```
python scripts/project-doctor.py --repo . --type Sub --wi "C:\projects\Workspace improve"
→ OK (1 warning: uncommitted canon-managed paths — expected pre-commit)

python scripts/sync-status.py --repo .
→ role: subordinate, Hub pending: 0, sync_state: stable
```
