"""SQLite manager for 1C help databases. One DB per platform version."""
import sqlite3
import json
from pathlib import Path
from datetime import datetime


SCHEMA_SQL = """
-- Метаданные БД
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);

-- Объекты: объекты платформы, типы, конструкции, глобальный контекст
CREATE TABLE IF NOT EXISTS syntax_objects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    full_name TEXT,
    category TEXT,
    parent_name TEXT,
    description TEXT,
    source TEXT
);

-- Методы, свойства, события
CREATE TABLE IF NOT EXISTS syntax_methods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    object_id INTEGER REFERENCES syntax_objects(id),
    name TEXT NOT NULL,
    kind TEXT,
    signature TEXT,
    params_json TEXT,
    returns TEXT,
    description TEXT,
    example TEXT,
    source TEXT
);

CREATE INDEX IF NOT EXISTS idx_methods_object ON syntax_methods(object_id);
CREATE INDEX IF NOT EXISTS idx_objects_name ON syntax_objects(name);
CREATE INDEX IF NOT EXISTS idx_objects_full_name ON syntax_objects(full_name);
"""

FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS help_search USING fts5(
    name, full_name, signature, description,
    tokenize='unicode61'
);
"""


def get_db_path(databases_dir: Path, version: str) -> Path:
    """Return path to DB file for given version."""
    version_safe = version.replace(".", "_").replace(" ", "_")
    return databases_dir / f"help_{version_safe}.db"


def create_database(db_path: Path, version: str) -> sqlite3.Connection:
    """Create new help database with schema. Returns connection."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
        ("version", version)
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
        ("created", datetime.now().isoformat())
    )
    conn.commit()
    return conn


def init_fts(conn: sqlite3.Connection) -> None:
    """Initialize FTS5 for search. Call after data is loaded."""
    try:
        conn.executescript(FTS_SQL)
    except sqlite3.OperationalError as e:
        if "already exists" not in str(e).lower():
            raise


def get_meta(conn: sqlite3.Connection) -> dict:
    """Get meta key-value pairs."""
    rows = conn.execute("SELECT key, value FROM meta").fetchall()
    return {r["key"]: r["value"] for r in rows}


def get_help_source_path(databases_dir: Path, version: str) -> str | None:
    """Return saved help source folder path for version, if any."""
    db_path = get_db_path(databases_dir, version)
    if not db_path.exists():
        return None
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT value FROM meta WHERE key = ?", ("source_path",)
        ).fetchone()
        conn.close()
        return row["value"] if row and row["value"] else None
    except Exception:
        return None


def list_databases(databases_dir: Path) -> list[dict]:
    """List all help databases with version info."""
    result = []
    if not databases_dir.exists():
        return result
    for f in databases_dir.glob("help_*.db"):
        try:
            conn = sqlite3.connect(str(f))
            conn.row_factory = sqlite3.Row
            meta = get_meta(conn)
            conn.close()
            result.append({
                "path": str(f),
                "version": meta.get("version", "?"),
                "created": meta.get("created", ""),
                "source_path": meta.get("source_path", ""),
            })
        except Exception:
            result.append({"path": str(f), "version": "?", "created": ""})
    return result
