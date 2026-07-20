"""Combined validation for metadata constructor projects (processor + report).

One entry point for both object views (was split as ``validate.py`` + ``validate_report.py``):
library ``validate()`` on the built trees + a per-module BSL check. A processor also checks
that command actions and declared form-event handlers have procedures in FormModule; reports
don't (the report form's handlers aren't validated here -- preserved behavior).

The BSL check delegates to ``help_tools.validate_code``, which is currently a disabled stub
(returned ~50 false positives : 1 real once help was loaded -- no variable-type tracking).
The loop is kept as the seam: when a real BSL linter replaces ``validate_code``, project
validation picks it up automatically. Until then ``bsl_errors`` is always empty.
"""
import re

from shared.constructor.export import build_trees, form_events_for_builder, validate_trees

HANDLER_RE = re.compile(
    r"(?:Процедура|Procedure|Функция|Function)\s+([\wЀ-ӿ]+)\s*\(",
    re.UNICODE | re.IGNORECASE,
)


def _event_handlers(project: dict) -> list[str]:
    """Handler procedure names required in FormModule for declared form events."""
    return [
        spec["handler"]
        for spec in (form_events_for_builder(project.get("form_events")) or [])
    ]


def _required_handlers(project: dict) -> list[str]:
    """Command actions + event handlers that need procedures in FormModule."""
    handlers = _event_handlers(project)
    for cmd in project.get("form_commands") or []:
        handlers.append(cmd.get("action") or cmd.get("name", ""))
    return [h for h in handlers if h]


def _find_handlers(code: str) -> set[str]:
    return {m.group(1) for m in HANDLER_RE.finditer(code)}


def validate(project: dict, kind: str, help_tools, version: str | None = None) -> dict:
    """Three-layer validation. Returns
    ``{ok, library_errors, bsl_errors, missing_handlers}``. ``kind``: ``'processor'`` |
    ``'report'`` -- only processors check missing command/event handlers."""
    roots = build_trees(project, kind)
    library_errors = validate_trees(roots)

    bsl_errors: list[dict] = []
    modules = project.get("modules") or {}
    for module_key, code in modules.items():
        if not code.strip():
            continue
        for e in help_tools.validate_code(code, version):
            err = dict(e)
            err["module"] = module_key
            bsl_errors.append(err)

    if kind == "processor":
        required = _required_handlers(project)
        defined = _find_handlers(modules.get("FormModule", ""))
        missing_handlers = [h for h in required if h not in defined]
    else:
        missing_handlers = []

    ok = not library_errors and not bsl_errors and not missing_handlers
    return {
        "ok": ok,
        "library_errors": library_errors,
        "bsl_errors": bsl_errors,
        "missing_handlers": missing_handlers,
    }
