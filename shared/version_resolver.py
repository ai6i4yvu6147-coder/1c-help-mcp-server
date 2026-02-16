"""Resolve platform version to database path: exact match or nearest."""
import re
from pathlib import Path


def parse_version(v: str) -> tuple[int, ...]:
    """Parse version string to tuple for comparison. E.g. '8.3.27' -> (8, 3, 27)."""
    if not v:
        return ()
    parts = re.findall(r"\d+", v)
    return tuple(int(p) for p in parts)


def get_available_versions(databases_dir: Path) -> list[tuple[str, Path]]:
    """Return list of (version, db_path) for all help DBs."""
    result = []
    if not databases_dir.exists():
        return result
    for f in databases_dir.glob("help_*.db"):
        # Extract version from filename: help_8_3_27.db -> 8.3.27
        name = f.stem
        if name.startswith("help_"):
            version_part = name[5:]  # after "help_"
            version = version_part.replace("_", ".")
            result.append((version, f))
    return result


def resolve_db_path(
    databases_dir: Path,
    version: str | None,
    default_version: str | None = None,
) -> Path | None:
    """
    Resolve version to database path.
    - If version specified: exact match, else nearest (lower then higher).
    - If version is None: use default_version, else latest.
    Returns None if no DB found.
    """
    available = get_available_versions(databases_dir)
    if not available:
        return None

    if version:
        target = parse_version(version)
        # Exact match
        for v, path in available:
            if parse_version(v) == target:
                return path
        # Nearest: prefer lower (older), then higher
        available_sorted = sorted(available, key=lambda x: parse_version(x[0]))
        lower = [x for x in available_sorted if parse_version(x[0]) <= target]
        higher = [x for x in available_sorted if parse_version(x[0]) > target]
        if lower:
            return lower[-1][1]
        if higher:
            return higher[0][1]
        return available_sorted[-1][1]

    # No version: use default or latest
    if default_version:
        return resolve_db_path(databases_dir, default_version, None)
    # Latest
    latest = max(available, key=lambda x: parse_version(x[0]))
    return latest[1]
