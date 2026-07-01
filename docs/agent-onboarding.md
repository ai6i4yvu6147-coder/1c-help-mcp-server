## Agent onboarding

### Project type

**Sub** (subordinate) — module `1c-help-mcp` in group `1c-cursor`.

| Field | Value |
|-------|-------|
| Head | `1c-admin-tool` |
| Head path | `C:/projects/1c-admin-tool` |
| Protocol canon | `C:/projects/1c-admin-tool/docs/group/shared/` |
| State | `stable` (epoch 0) — see [`group/integration.md`](group/integration.md) |

The portable MCP server is **autonomous**: help and tools work without the Hub. Integration with Admin Hub — via packet-based docs sync after protocol `stable`.

### Project summary

The project indexes unpacked 1C platform help (`shcntx_ru`, `shlang_ru`, `shquery_ru`) into SQLite and exposes MCP tools for BSL syntax assistance, query language, and heuristic code validation.

### Key policies (do not violate)

- **NO_DB_MIGRATIONS**: never write migrations/conversions for existing SQLite databases in `databases/`. After schema/import logic changes, databases are **always recreated** via `admin_tool` from help sources.
- **Testing**: functional verification uses the «live» MCP after the user rebuilds the server and reconnects MCP in the agent. Verification — **only via MCP tool calls**, starting with `list_help_versions`; no direct SQLite reads and no Python workaround scripts.
- **Sources vs runtime (portable)**: repository sources must not contain runtime state (`databases/*.db`). Databases live in the portable instance (`../1c_help_mcp_server_Portable/databases/`) and are created via Admin.
- **Responsibility split**: the agent changes sources; the user rebuilds portable/server and recreates databases if needed; the agent verifies via MCP tools.
- **Parser: rely on real HBK**: when extending `shared/help_parser.py` / `shared/query_parser.py`, inspect real HTML from unpacked help. Sources live outside the repo (folder with `shcntx_ru` / `shlang_ru` / `shquery_ru`).
- **BSL vs query language**: built-in language — `get_syntax`, `search_syntax`; query text (`ВЫБРАТЬ`, `ЕСТЬNULL`) — `get_query_syntax`, `search_query`, `list_query_topics`.
- **Group-sync**: shared protocol canon — only in Head `docs/group/shared/`. Sub updates local specs from **packets** in `docs/group/inbox/`; do not commit sync packets. Group-critical changes — via outbox; outbox→inbox delivery — **operator** per [`group/OPERATOR-HANDOFF.md`](group/OPERATOR-HANDOFF.md); processing — skill **`sync`**.

### Terms

- **«Live MCP»**: server **already connected in the IDE**; verification — actual tool calls.
- The IDE connection name may differ from the exe name. Rely on available tools (`list_help_versions`, `get_syntax`, …) and their responses.

### Normalization and canons

| Path | Purpose |
|------|---------|
| `docs/canons/` | Local WI standards copy (canon **2.4.0**) |
| `group.manifest.yaml` | Sub role, module id, Head reference |
| `scripts/project-doctor.py` | Structure check |
| `docs/group/OPERATOR-HANDOFF.md` | Manual Head ↔ Sub packet delivery (operator) |
| `docs/group/templates/` | Sync packet templates |
| `.cursor/skills/` | **4 skills** — `normalize-project`, `canon-align`, `maintain-docs`, `sync` |
| `.cursor/agents/` | **1 subagent** — `doc-librarian` |
| `docs/normalize-record.md` | Last normalize record |

Re-normalize: command `/re-normalize` (see `.cursor/commands/re-normalize.md`) or initiator `subordinate.md` from Workspace improve.

### Quick links

- Backlog: `todo.md`
- Architecture: `architecture.md`
- MCP tools: `mcp-tools.md`
- SQLite: `database.md`
- Testing protocol: `testing-protocol.md`
- Group integration: `group/integration.md`
- Canons: `canons/README.md`
