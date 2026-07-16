"""Admin Hub thin CLI for 1C Help MCP.

help-mcp has no full Admin-Hub protocol surface yet; this CLI currently exposes
only ``tool-calls`` so the Hub «журнал по задаче» viewer can read this Sub's
journal uniformly with config-mcp / data-mcp (protocol v1.0.7 §3.4). The store
is ``<root>/logs/tool-calls.db`` — the same path the server writes to.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.tool_calls_log import READ_DEFAULT_LIMIT, read_tool_calls, tool_calls_db_path

MODULE_ID = "1c-help-mcp"
MODULE_TYPE = "help-mcp"

EXIT_SUCCESS = 0
EXIT_VALIDATION = 1
EXIT_IO = 2
EXIT_RUNTIME = 3


def _write_json_stdout(payload: object) -> None:
    """UTF-8 JSON to stdout without BOM (Admin Hub CLI convention)."""
    data = json.dumps(payload, ensure_ascii=False, indent=2)
    sys.stdout.buffer.write(data.encode("utf-8"))
    sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.flush()


def _resolve_root(explicit_root: Path | None) -> Path:
    """Module root: --root, else frozen exe.parent.parent, else repo root.

    Mirrors the server's resolution so both read/write the same ``logs/`` dir.
    """
    if explicit_root is not None:
        return Path(explicit_root).resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent.parent
    return Path(__file__).resolve().parents[1]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="1c-help-cli",
        description="1C Help MCP — Admin Hub protocol CLI",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Portable module root (overrides auto-detect)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    calls_sp = sub.add_parser("tool-calls", help="Read tool-call journal rows (JSON)")
    calls_sp.add_argument("--task-id", default=None, help="Filter by task_id (exact)")
    calls_sp.add_argument("--tool", default=None, help="Filter by tool name (exact)")
    calls_sp.add_argument("--since", default=None, help="Keep rows with ts_utc >= SINCE (ISO-8601 Z)")
    calls_sp.add_argument("--until", default=None, help="Keep rows with ts_utc <= UNTIL (ISO-8601 Z)")
    calls_sp.add_argument("--only-errors", action="store_true", help="Only failed calls (success = 0)")
    calls_sp.add_argument(
        "--limit",
        type=int,
        default=READ_DEFAULT_LIMIT,
        help=f"Max rows, newest first (default: {READ_DEFAULT_LIMIT})",
    )
    calls_sp.add_argument("--offset", type=int, default=0, help="Rows to skip (pagination)")
    calls_sp.add_argument(
        "--json",
        action="store_true",
        default=True,
        help="JSON output on stdout (default: true)",
    )

    return parser


def run_tool_calls(args: argparse.Namespace) -> dict:
    """Read the module's tool-call journal into a Hub-uniform JSON envelope."""
    root = _resolve_root(args.root)
    db_path = tool_calls_db_path(root / "logs")
    rows = read_tool_calls(
        db_path,
        task_id=args.task_id,
        tool=args.tool,
        since=args.since,
        until=args.until,
        only_errors=args.only_errors,
        limit=args.limit,
        offset=args.offset,
    )
    return {
        "module": MODULE_ID,
        "moduleType": MODULE_TYPE,
        "db": str(db_path),
        "query": {
            "taskId": args.task_id,
            "tool": args.tool,
            "since": args.since,
            "until": args.until,
            "onlyErrors": bool(args.only_errors),
            "limit": args.limit,
            "offset": args.offset,
        },
        "count": len(rows),
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "tool-calls":
            payload = run_tool_calls(args)
        else:
            print(f"Unknown command: {args.command}", file=sys.stderr)
            return EXIT_VALIDATION
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_IO
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_VALIDATION
    except Exception as exc:  # noqa: BLE001 - surface as runtime error, never crash
        print(str(exc), file=sys.stderr)
        return EXIT_RUNTIME

    _write_json_stdout(payload)
    return EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(main())
