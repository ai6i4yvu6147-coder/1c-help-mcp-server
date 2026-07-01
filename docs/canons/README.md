# Project structure canons

Universal standards for **all** repositories.

## Reading order

1. `project-structure.md` — S / H / Sub, base layout
2. `documentation.md` — docs hierarchy, language tiers
3. `normalize-governance.md` — agent-first normalize
4. `normalize-merge.md` — merge with existing repo
5. `group-sync.md` — packet sync, protocol reconcile

## Versioning

| Version | Date | Change |
|---------|------|--------|
| 2.0.0 | 2026-06-29 | Universal S / H / Sub model |
| 2.1.0 | 2026-06-29 | Packet sync inbox/outbox |
| 2.2.0 | 2026-06-30 | Agent-first normalize; protocol states; 2 subagents |
| 2.3.0 | 2026-07-01 | Skills sync/sync-base; operator handoff; `normalize.deprecations.yaml` |
| 2.4.0 | 2026-07-02 | Agent-cache tier English; language migration on re-normalize |

## Artifacts

| Artifact | Path |
|----------|------|
| Templates | `../../templates/` |
| Initiators | `../../initiators/` |
| Checklist | `../../normalize.bundle.yaml` |
| Deprecations | `../../normalize.deprecations.yaml` |
| Check | `../../scripts/project-doctor.py` |
| Snapshot / status | `../../scripts/protocol-snapshot.py`, `../../scripts/sync-status.py` |

## Artifacts in this repository

Local paths for **1c-help-mcp** (Sub, group `1c-cursor`):

| Artifact | Path |
|----------|------|
| Group manifest | `group.manifest.yaml` |
| Group integration | `docs/group/integration.md` |
| Operator handoff | `docs/group/OPERATOR-HANDOFF.md` |
| Packet templates | `docs/group/templates/` |
| Protocol baseline | `docs/group/protocol-ref/epoch0/` |
| Structure check | `scripts/project-doctor.py` |
| Sync status | `scripts/sync-status.py` |
| Protocol snapshot | `scripts/protocol-snapshot.py` |
| Subagent | `.cursor/agents/doc-librarian.md` |
| Skills (4) | `.cursor/skills/normalize-project/`, `canon-align/`, `maintain-docs/`, `sync/` |
| Normalize record | `docs/normalize-record.md` |
