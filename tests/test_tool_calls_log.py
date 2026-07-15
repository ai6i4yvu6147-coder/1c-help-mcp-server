from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.tool_calls_log import (
    ToolCallLogger,
    build_args_summary,
    extract_correlation,
    inject_correlation_properties,
    tool_calls_db_path,
)


class _FakeTool:
    def __init__(self, input_schema: dict) -> None:
        self.inputSchema = input_schema


def _read_rows(db_path: Path) -> list[sqlite3.Row]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        return list(conn.execute("SELECT * FROM tool_calls ORDER BY id"))
    finally:
        conn.close()


def test_tool_calls_db_path_under_logs_dir(tmp_path: Path) -> None:
    assert tool_calls_db_path(tmp_path / "logs") == tmp_path / "logs" / "tool-calls.db"


def test_extract_correlation_reads_trio_from_input() -> None:
    corr = extract_correlation(
        {"task_id": 1024, "agent": "cursor", "model": "claude-opus-4-8", "version": "8.3.27"}
    )
    assert corr == {"task_id": "1024", "agent": "cursor", "model": "claude-opus-4-8"}


def test_extract_correlation_absent_is_none() -> None:
    assert extract_correlation({"version": "8.3.27"}) == {
        "task_id": None,
        "agent": None,
        "model": None,
    }


def test_build_args_summary_folds_scope_and_drops_trio() -> None:
    summary = build_args_summary(
        {"task_id": "1024", "agent": "x", "model": "y", "name": "Сообщить", "version": "8.3.27"}
    )
    assert summary is not None
    assert '"version":"8.3.27"' in summary
    assert '"name":"Сообщить"' in summary
    assert "task_id" not in summary


def test_build_args_summary_redacts_password() -> None:
    summary = build_args_summary({"password": "hunter2"})
    assert summary == '{"password":"***"}'


def test_build_args_summary_caps_length() -> None:
    summary = build_args_summary({"code": "x" * 5000}, max_chars=100)
    assert summary is not None
    assert len(summary) == 100
    assert summary.endswith("…")


def test_build_args_summary_empty_is_none() -> None:
    assert build_args_summary({"task_id": "1"}) is None


def test_inject_correlation_properties_adds_trio() -> None:
    tool = _FakeTool(
        {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}
    )
    inject_correlation_properties([tool])
    props = tool.inputSchema["properties"]
    assert set(props) == {"name", "task_id", "agent", "model"}
    assert tool.inputSchema["required"] == ["name"]


def test_logger_writes_success_row(tmp_path: Path) -> None:
    db_path = tmp_path / "logs" / "tool-calls.db"
    logger = ToolCallLogger(db_path)
    logger.log(
        tool="get_syntax",
        started_at="2026-07-16T07:00:00Z",
        started_mono=0.0,
        args={"task_id": "t1", "agent": "cursor", "model": "opus", "name": "Сообщить", "version": "8.3.27"},
        success=True,
        result_bytes=256,
    )

    row = _read_rows(db_path)[0]
    assert row["tool"] == "get_syntax"
    assert row["task_id"] == "t1"
    assert row["agent"] == "cursor"
    assert row["model"] == "opus"
    assert row["success"] == 1
    assert row["error_code"] is None
    assert row["result_bytes"] == 256
    assert '"version":"8.3.27"' in row["args_summary"]
    assert row["pid"] is not None


def test_logger_writes_error_row(tmp_path: Path) -> None:
    db_path = tmp_path / "logs" / "tool-calls.db"
    logger = ToolCallLogger(db_path)
    logger.log(
        tool="validate_code",
        started_at="2026-07-16T07:01:00Z",
        started_mono=0.0,
        args={"version": "8.3.27"},
        success=False,
        error_code="KeyError",
    )

    row = _read_rows(db_path)[0]
    assert row["success"] == 0
    assert row["error_code"] == "KeyError"
    assert row["task_id"] is None


def test_logger_swallows_write_errors(tmp_path: Path) -> None:
    db_path = tmp_path / "logs" / "tool-calls.db"
    db_path.parent.mkdir(parents=True)
    db_path.mkdir()  # occupy the db path with a directory so sqlite open fails
    logger = ToolCallLogger(db_path)
    logger.log(
        tool="get_syntax",
        started_at="2026-07-16T07:00:00Z",
        started_mono=0.0,
        args={"version": "8.3.27"},
        success=True,
    )  # must not raise
