"""Combined validation for metadata constructor projects."""
import re

from shared.constructor.export import build_trees, form_events_for_builder, validate_trees

HANDLER_RE = re.compile(
    r"(?:Процедура|Procedure|Функция|Function)\s+([\w\u0400-\u04FF]+)\s*\(",
    re.UNICODE | re.IGNORECASE,
)


def _event_handlers(proc: dict) -> list[str]:
    """Handler procedure names required in FormModule for declared form events."""
    return [
        spec["handler"]
        for spec in (form_events_for_builder(proc.get("form_events")) or [])
    ]


def _required_handlers(proc: dict) -> list[str]:
    """Collect command actions and event handlers that need procedures in FormModule."""
    handlers = _event_handlers(proc)
    for cmd in proc.get("form_commands") or []:
        handlers.append(cmd.get("action") or cmd.get("name", ""))
    return [h for h in handlers if h]


def _find_handlers(code: str) -> set[str]:
    return {m.group(1) for m in HANDLER_RE.finditer(code)}


def validate_project(proc: dict, help_tools, version: str | None = None) -> dict:
    """
    Three-layer validation. Returns structured result:
    {ok: bool, library_errors: [...], bsl_errors: [...], missing_handlers: [...]}
    """
    object_root, form_descriptor_root, form_layout_root = build_trees(proc)
    library_errors = validate_trees(object_root, form_descriptor_root, form_layout_root)

    bsl_errors: list[dict] = []
    modules = proc.get("modules") or {}
    for module_key, code in modules.items():
        if not code.strip():
            continue
        errors = help_tools.validate_code(code, version)
        for e in errors:
            e = dict(e)
            e["module"] = module_key
            bsl_errors.append(e)

    required = _required_handlers(proc)
    form_code = modules.get("FormModule", "")
    defined = _find_handlers(form_code)
    missing_handlers = [h for h in required if h not in defined]

    ok = not library_errors and not bsl_errors and not missing_handlers
    return {
        "ok": ok,
        "library_errors": library_errors,
        "bsl_errors": bsl_errors,
        "missing_handlers": missing_handlers,
    }
