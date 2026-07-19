"""Cross-repo write↔read contract for the *forms* format on the single engine.

The constructor (this repo, H-MCP) writes ``Forms/<name>/Ext/Form.xml`` via the library's
``build_form_layout``; the configuration indexer (C-MCP) reads every form back via the same
library's ``read_form``. Nothing pins those two halves together — ``1c-metadata-schema`` is an
unpinned editable install shared by both consumers (``build_all.bat`` picks the first path that
exists; there is no version constraint). So a drift on either side — the writer emitting a shape
the reader no longer understands, or the reader's contract changing under the indexer — would
only surface later, at rebuild time, in a *different* repository.

These round-trips close that gap: drive the **real** constructor export, then parse the emitted
``Form.xml`` back with ``read_form`` (the exact function C-MCP depends on) and assert that what
was written survives — attribute names and their resolved type slots, the item tree and its
nesting, commands, and event handlers. If the engine's form write/read contract diverges, this
fails here, in CI, instead of silently in a downstream rebuild.

See ``docs/write-tools-taxonomy.md`` (write side) and C-MCP ``docs/forms-engine-migration.md``
(read side) for the two halves being pinned together here.
"""
from pathlib import Path

from onec_metadata_schema import read_form
from server.constructor_tools import ConstructorTools


class _StubHelp:
    """``export`` runs only the library's XML validation, never BSL — but the facade
    constructor requires a help handle, so hand it an inert one."""

    def validate_code(self, code, version=None):
        return []


def _build_and_read_form(tmp_path, *, fields, groups=None, commands=None, events=None):
    """Create a processor, set its form spec, export the project, and read the emitted
    ``Form.xml`` back through the library. Returns the ``read_form`` model dict."""
    ct = ConstructorTools(tmp_path / "constructor.db", _StubHelp())
    ct.create("processor", "РТФорма", "Round-trip форма")
    ct.set_form_any(
        "РТФорма", fields=fields, groups=groups, commands=commands, events=events
    )
    ct.export("РТФорма", str(tmp_path / "out"))

    form_xml = (
        tmp_path / "out" / "РТФорма" / "РТФорма" / "Forms" / "Форма" / "Ext" / "Form.xml"
    )
    assert form_xml.exists(), "export did not write the form layout"
    return read_form(form_xml.read_bytes())


def test_processor_form_structure_roundtrips(tmp_path):
    """Fields, a nested group, a command and an event handler written by the constructor
    all come back out of ``read_form`` with names, item tree, nesting and handlers intact."""
    model = _build_and_read_form(
        tmp_path,
        fields=[
            {"name": "Орг", "type_raw": "cfg:CatalogRef.Организации"},
            {"name": "Сумма", "type_raw": "xs:decimal"},
        ],
        groups=[
            {
                "name": "Группа1",
                "title_ru": "Группа",
                "fields": [{"name": "Комментарий", "type_raw": "xs:string"}],
            }
        ],
        commands=[{"name": "Обновить", "title_ru": "Обновить"}],
        events=[{"event": "OnOpen", "handler": "ПриОткрытии"}],
    )

    # Form attributes: every field (flat and grouped) got a matching scalar Attribute,
    # alongside the mandatory main attribute the builder always emits (`Объект`).
    attr_names = {a["name"] for a in model["attributes"]}
    assert {"Орг", "Сумма", "Комментарий"} <= attr_names
    assert any(a["is_main"] for a in model["attributes"])

    # Items: each field is an InputField; the group is a container and its field nests
    # under it (`parent_id` -> the group's `id` — the shared ui_ids counter round-trips).
    items = {i["name"]: i for i in model["items"] if i["name"]}
    assert {"Орг", "Сумма", "Группа1", "Комментарий"} <= set(items)
    assert items["Группа1"]["type"] == "UsualGroup"
    assert items["Комментарий"]["parent_id"] == items["Группа1"]["id"]
    assert items["Группа1"]["parent_id"] is None

    # Command and event handler survive the trip.
    assert "Обновить" in {c["name"] for c in model["commands"]}
    assert any(
        e["name"] == "OnOpen" and e["handler"] == "ПриОткрытии" for e in model["events"]
    )


def test_processor_form_attribute_types_roundtrip(tmp_path):
    """Type slots are the core of what the indexer stores — assert an object reference and a
    primitive both come back through ``read_form`` with their resolved shape (not just names)."""
    model = _build_and_read_form(
        tmp_path,
        fields=[
            {"name": "Орг", "type_raw": "cfg:CatalogRef.Организации"},
            {"name": "Сумма", "type_raw": "xs:decimal"},
        ],
    )
    by_name = {a["name"]: a for a in model["attributes"]}

    org_slots = by_name["Орг"]["type_slots"]
    assert any(
        s.get("kind") == "object_ref"
        and s.get("ref_suffix") == "CatalogRef"
        and s.get("ref_name") == "Организации"
        for s in org_slots
    ), org_slots

    sum_slots = by_name["Сумма"]["type_slots"]
    assert any(
        s.get("kind") == "primitive" and s.get("base_type") == "Number"
        for s in sum_slots
    ), sum_slots
