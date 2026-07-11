# TODO

## Hub pending

## Admin Hub / group integration

- **Status:** `stable`, epoch 0 (see [`group/integration.md`](group/integration.md))
- **Layout 2.5.0:** 1 subagent (`doc-librarian`); 4 skills — `normalize-project`, `canon-align`, `maintain-docs`, `sync`
- Hub sync via `C:/projects/1c-admin-tool/GROUP-HUB.md` · `C:/repo/1c-config-admin-tool/GROUP-HUB.md`; skill **`sync`** when `## Hub pending` has items

## Product

- Support current 1C help versions via Admin
- Keep MCP tools documentation (`docs/mcp-tools.md`) up to date
- Testing per [`testing-protocol.md`](testing-protocol.md)

### Metadata constructor — Stage E (`ready`)

Canon: [`metadata-constructor-plan.md`](metadata-constructor-plan.md), Head `metadata-library-cluster.md`. Library `1c-metadata-schema` Stages C–D **done** — blocker on reference export **removed**.

- [ ] Add `pip install -e C:/projects/1c-metadata-schema` to `requirements.txt` (import `onec_metadata_schema`)
- [ ] New subsystem `shared/constructor/` + SQLite `constructor.db` (separate from help DBs)
- [ ] MCP tools: `create_processor`, `set_attributes`, `set_form`, `set_module_code`, `validate_project`, `export_project`
- [ ] `validate_project`: library `validate()` + existing BSL validation + form Event/Command.Action handler presence check
- [ ] **First E2E:** agent dialog reproducing `обр ТестПорядка` (or simpler) → manual Configurator load — readiness criterion

## Tech debt

- No automated unit tests (`tests/` reserved for future use)
