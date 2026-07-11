"""Combined validation for external report constructor projects."""
from shared.constructor.export_report import build_trees, validate_trees


def validate_report(report: dict, help_tools, version: str | None = None) -> dict:
    """Library validate() + optional BSL check on ObjectModule (and FormModule, for
    layout/"macet" reports)."""
    roots = build_trees(report)
    library_errors = validate_trees(roots)

    bsl_errors: list[dict] = []
    modules = report.get("modules") or {}
    for module_key, code in modules.items():
        if not code.strip():
            continue
        for e in help_tools.validate_code(code, version):
            err = dict(e)
            err["module"] = module_key
            bsl_errors.append(err)

    ok = not library_errors and not bsl_errors
    return {
        "ok": ok,
        "library_errors": library_errors,
        "bsl_errors": bsl_errors,
        "missing_handlers": [],
    }
