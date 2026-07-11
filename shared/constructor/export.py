"""Build and write external data processor file trees."""
from pathlib import Path

from onec_metadata_schema import serialize, validate
from onec_metadata_schema.builder import (
    build_external_data_processor,
    build_form_descriptor,
    build_form_layout,
)

# Common form handler -> platform event name (legacy string events in DB).
_HANDLER_TO_EVENT = {
    "ПриОткрытии": "OnOpen",
    "ПриЗакрытии": "OnClose",
    "ПриСозданииНаСервере": "OnCreateAtServer",
}


def form_events_for_builder(form_events: list | None) -> list[dict] | None:
    """Normalize stored form_events to build_form_layout events=[{event, handler}, ...]."""
    if not form_events:
        return None
    result: list[dict] = []
    for entry in form_events:
        if isinstance(entry, str):
            handler = entry
            event = _HANDLER_TO_EVENT.get(handler)
            if not event:
                raise ValueError(
                    f"событие «{handler}»: укажите {{event, handler}}, "
                    f"например {{event: 'OnOpen', handler: 'ПриОткрытии'}}"
                )
            result.append({"event": event, "handler": handler})
        elif isinstance(entry, dict):
            if entry.get("event") and entry.get("handler"):
                result.append({"event": entry["event"], "handler": entry["handler"]})
            else:
                handler = entry.get("handler") or entry.get("name", "")
                event = entry.get("event") or _HANDLER_TO_EVENT.get(handler, "")
                if not event or not handler:
                    raise ValueError(
                        f"событие {entry!r}: нужны event и handler "
                        f"(например event='OnOpen', handler='ПриОткрытии')"
                    )
                result.append({"event": event, "handler": handler})
    return result or None


def build_trees(proc: dict) -> tuple:
    """Build object, form descriptor, and form layout Node trees from processor dict."""
    name = proc["name"]
    form_name = proc.get("form_name") or "Форма"
    form_synonym = proc.get("form_synonym_ru") or form_name

    object_root = build_external_data_processor(
        name=name,
        synonym_ru=proc["synonym_ru"],
        attributes=proc.get("attributes", []),
        form_name=form_name,
    )
    form_descriptor_root = build_form_descriptor(form_name, form_synonym)
    form_layout_root = build_form_layout(
        object_type_raw=f"cfg:ExternalDataProcessorObject.{name}",
        fields=proc.get("form_fields") or None,
        groups=proc.get("form_groups") or None,
        commands=proc.get("form_commands") or None,
        events=form_events_for_builder(proc.get("form_events")),
    )
    return object_root, form_descriptor_root, form_layout_root


def validate_trees(object_root, form_descriptor_root, form_layout_root) -> list[str]:
    """Run library validate() on all three roots."""
    return (
        validate(object_root)
        + validate(form_descriptor_root)
        + validate(form_layout_root)
    )


def export_project(proc: dict, parent_dir: Path) -> dict:
    """
    Build, validate, and write processor under parent_dir/<Name>/.

    `parent_dir` is the export container (e.g. fullAI/). Each processor gets its own
    subdirectory. 1C resolves child paths from the root XML directory plus object name:

        parent_dir/HelloWorld/HelloWorld.xml
        parent_dir/HelloWorld/HelloWorld/Forms/...

    Returns {processor, parent_dir, processor_dir, files} where files are relative
    to parent_dir. Raises ValueError on validation errors.
    """
    object_root, form_descriptor_root, form_layout_root = build_trees(proc)
    errors = validate_trees(object_root, form_descriptor_root, form_layout_root)
    if errors:
        raise ValueError("ошибки validate():\n" + "\n".join(f"  - {e}" for e in errors))

    name = proc["name"]
    form_name = proc.get("form_name") or "Форма"
    parent_dir = Path(parent_dir)
    processor_dir = parent_dir / name
    content_dir = processor_dir / name
    written: list[str] = []

    root_xml = processor_dir / f"{name}.xml"
    root_xml.parent.mkdir(parents=True, exist_ok=True)
    root_xml.write_text(serialize(object_root), encoding="utf-8")
    written.append(str(root_xml.relative_to(parent_dir)))

    form_desc_path = content_dir / "Forms" / f"{form_name}.xml"
    form_desc_path.parent.mkdir(parents=True, exist_ok=True)
    form_desc_path.write_text(serialize(form_descriptor_root), encoding="utf-8")
    written.append(str(form_desc_path.relative_to(parent_dir)))

    form_layout_path = content_dir / "Forms" / form_name / "Ext" / "Form.xml"
    form_layout_path.parent.mkdir(parents=True, exist_ok=True)
    form_layout_path.write_text(serialize(form_layout_root), encoding="utf-8")
    written.append(str(form_layout_path.relative_to(parent_dir)))

    modules = proc.get("modules") or {}
    object_code = modules.get("ObjectModule", "")
    if object_code:
        obj_mod_path = content_dir / "Ext" / "ObjectModule.bsl"
        obj_mod_path.parent.mkdir(parents=True, exist_ok=True)
        obj_mod_path.write_text(object_code, encoding="utf-8")
        written.append(str(obj_mod_path.relative_to(parent_dir)))

    form_code = modules.get("FormModule", "")
    if form_code:
        form_mod_path = content_dir / "Forms" / form_name / "Ext" / "Form" / "Module.bsl"
        form_mod_path.parent.mkdir(parents=True, exist_ok=True)
        form_mod_path.write_text(form_code, encoding="utf-8")
        written.append(str(form_mod_path.relative_to(parent_dir)))

    return {
        "processor": name,
        "parent_dir": str(parent_dir),
        "processor_dir": str(processor_dir),
        "open_in_configurator": str(root_xml),
        "files": written,
    }
