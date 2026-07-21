# 1C Help MCP Server

For AI agents and developers: see [`docs/`](docs/) (start with [`docs/agent-map.md`](docs/agent-map.md)).

1C syntax help for AI agents (syntax assistant and code validation).

## Quick start

1. Build: `build_all.bat` → creates `1c_help_mcp_server_Portable` in the parent folder.
2. In Portable: `Admin.bat` → «Add help» → folder with `shcntx_ru`, `shlang_ru`, and `shquery_ru` → version (8.3.27).
3. MCP: add a `command` in the client config pointing to `Server\1c-help-server.exe` inside the portable folder.
4. BSL tools: `get_syntax`, `search_syntax`, `get_object_api`, `list_syntax`, `list_help_versions`.
5. Query tools: `get_query_syntax`, `search_query`, `list_query_topics`.

## Project layout (sources)

| Path | Purpose |
|------|---------|
| `admin_tool/` | Admin GUI |
| `server/` | MCP server |
| `shared/` | parser, db_manager, version_resolver |
| `docs/` | documentation for AI and developers |
| `config.json` | dev: `databases_dir = databases` |
| `build_all.bat` | build → `../1c_help_mcp_server_Portable/` |

## Help source

Extract `shcntx_ru.hbk`, `shlang_ru.hbk`, and `shquery_ru.hbk` from the 1C platform `bin` folder (7zip: Extract).
The path to extracted folders is set in Admin on import — not stored in the repository.

## Portability

The portable build can be moved. After moving, update the exe path in the MCP client config.

## Tests

`pip install -r requirements-dev.txt` then `pytest` (was previously missing from the dev venv; unlike `1c-config-mcp`/`1c-data-mcp`, run tests manually — no CI workflow here).
