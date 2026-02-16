# -*- coding: utf-8 -*-
"""Parser for shcntx_ru and shlang_ru (unpacked HBK help)."""
import re
from pathlib import Path
from bs4 import BeautifulSoup
from typing import Iterator


def _extract_text(el) -> str:
    """Get text content, stripping tags."""
    if el is None:
        return ""
    return el.get_text(separator=" ", strip=True) if hasattr(el, "get_text") else str(el)


def _parse_method_page(html_path: Path, base_object: str, source: str) -> dict | None:
    """Parse a method HTML file. Returns method dict or None."""
    try:
        with open(html_path, encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "lxml")
    except Exception:
        return None

    pagetitle = soup.find(class_="V8SH_pagetitle")
    heading = soup.find(class_="V8SH_heading")
    if not pagetitle:
        return None

    title_text = _extract_text(pagetitle)
    # Format: "Object.Method (Object.Method)" or "Object.Method"
    method_name = _extract_text(heading) if heading else ""
    if not method_name and "(" in title_text:
        # Extract from title: "СправочникМенеджер.Выбрать (Select)" -> Выбрать
        ru_part = title_text.split("(")[0].strip().split(".")[-1].strip()
        if ru_part:
            method_name = ru_part

    signature = ""
    params = []
    returns = ""
    description = ""

    for el in soup.find_all(class_="V8SH_chapter"):
        label = _extract_text(el).lower()
        rest = []
        for sib in el.next_siblings:
            if hasattr(sib, "name") and sib.name and sib.get("class") and "V8SH_chapter" in sib.get("class", []):
                break
            t = _extract_text(sib) if hasattr(sib, "get_text") else (str(sib) if sib else "")
            if t:
                rest.append(t)
        text = " ".join(rest).strip()[:2000]

        if "синтаксис" in label:
            signature = text.split("\n")[0].strip()
        elif "параметры" in label:
            pass  # params from V8SH_rubric
        elif "возвращаемое" in label or "возвраща" in label:
            returns = text[:500]
        elif "описание" in label:
            description = text[:2000]

    # Parse params from V8SH_rubric
    for rub in soup.find_all(class_="V8SH_rubric"):
        ptext = _extract_text(rub)
        # Format: "<Имя> (необязательный)" or "<Имя>"
        match = re.search(r"<([^>]+)>\s*(\([^)]*\))?", ptext)
        if match:
            pname = match.group(1).strip()
            optional = "необязательн" in (match.group(2) or "").lower()
            # Find type - next text often has "Тип: ..."
            desc_parts = []
            for sib in rub.next_siblings:
                if hasattr(sib, "get_text"):
                    t = _extract_text(sib)
                else:
                    t = str(sib) if sib else ""
                if t:
                    desc_parts.append(t)
                if hasattr(sib, "name") and sib.name == "div" and sib.get("class"):
                    break
            full_desc = " ".join(desc_parts)[:300]
            ptype = ""
            if "Тип:" in full_desc or "тип:" in full_desc:
                m = re.search(r"[Тт]ип:\s*([^.<\n]+)", full_desc)
                if m:
                    ptype = m.group(1).strip()
            params.append({"name": pname, "type": ptype or "Любой", "optional": optional})

    return {
        "name": method_name,
        "kind": "Method",
        "signature": signature,
        "params": params,
        "returns": returns,
        "description": description,
        "source": source,
    }


def _parse_object_page(soup: BeautifulSoup, source: str) -> dict | None:
    """Extract object info and method links from object page."""
    pagetitle = soup.find(class_="V8SH_pagetitle")
    title = soup.find(class_="V8SH_title")
    if not pagetitle:
        return None

    full_name = _extract_text(pagetitle).split("(")[0].strip()
    name = full_name.split(".")[-1] if "." in full_name else full_name
    if title:
        name = _extract_text(title).split("(")[0].strip()
        if "." in name:
            name = name.split(".")[-1]

    description = ""
    for el in soup.find_all(class_="V8SH_chapter"):
        if "описание" in _extract_text(el).lower():
            parts = []
            for sib in el.next_siblings:
                if hasattr(sib, "name") and sib.name and sib.get("class") and "V8SH_chapter" in (sib.get("class") or []):
                    break
                t = _extract_text(sib) if hasattr(sib, "get_text") else (str(sib) if sib else "")
                if t:
                    parts.append(t)
            description = " ".join(parts)[:2000]
            break

    methods = []
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        text = _extract_text(a)
        if not text:
            continue
        # Method link: object128/methods/Select254.html or methods/Select254.html
        if "/methods/" in href or "methods" in href:
            mname = text.split("(")[0].strip()
            if mname and mname not in [x["name"] for x in methods]:
                methods.append({"name": mname, "kind": "Method", "signature": None, "params": [], "returns": None, "description": None, "source": source})
        # Property
        elif "properties/" in href:
            mname = text.split("(")[0].strip()
            if mname:
                methods.append({"name": mname, "kind": "Property", "signature": None, "params": [], "returns": None, "description": None, "source": source})
        # Event
        elif "events/" in href:
            mname = text.split("(")[0].strip()
            if mname:
                methods.append({"name": mname, "kind": "Event", "signature": None, "params": [], "returns": None, "description": None, "source": source})

    return {
        "name": name,
        "full_name": full_name,
        "category": "object",
        "description": description,
        "methods": methods,
        "source": source,
    }


def _parse_shlang_item(html_path: Path, category: str, source: str) -> dict | None:
    """Parse shlang_ru item: type (def_*) or structure (struct_*)."""
    try:
        with open(html_path, encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "lxml")
    except Exception:
        return None

    pagetitle = soup.find(class_="V8SH_pagetitle")
    title = soup.find(class_="V8SH_title")
    if not pagetitle:
        return None

    full_name = _extract_text(pagetitle).split("(")[0].strip()
    name = full_name

    description = ""
    signature = ""
    params = []

    for p in soup.find_all("p", class_="Usual"):
        text = _extract_text(p)
        if not text:
            continue
        if text.startswith("Синтаксис:") or (text.startswith("Синтаксис") and ":" in text):
            signature = text.split(":", 1)[-1].strip()[:500]
        elif text.startswith("Описание:") or "Описание" in text[:20]:
            description = text.split(":", 1)[-1].strip()[:2000] if ":" in text else text[:2000]
        elif "<" in text and ">" in text and "Параметры" not in text:
            m = re.search(r"<([^>]+)>", text)
            if m:
                params.append({"name": m.group(1), "type": "", "optional": "необязательн" in text.lower()})

    methods = []
    kind = "Structure" if category == "structure" else "Type"
    methods.append({"name": name, "kind": kind, "signature": signature or None, "params": params, "returns": None, "description": description, "source": source})

    return {
        "name": name,
        "full_name": full_name,
        "category": category,
        "description": description or full_name,
        "methods": methods,
        "source": source,
    }


def _walk_shcntx_objects(shcntx: Path) -> Iterator[tuple[Path, Path | None]]:
    """Yield (object_html_path, method_dir_path) for objects that have methods."""
    objects_dir = shcntx / "objects"
    if not objects_dir.exists():
        return

    for html_file in objects_dir.rglob("*.html"):
        if html_file.name.startswith("__"):
            continue
        rel = html_file.relative_to(objects_dir)
        # Пропускаем страницы методов/свойств — это не объекты
        if "/methods/" in rel.as_posix() or "/properties/" in rel.as_posix():
            continue
        # Методы лежат в подпапке ObjectName/methods/ (не в родительской methods/)
        method_dir = html_file.parent / html_file.stem / "methods"
        yield html_file, method_dir if method_dir.exists() else None


def parse_help_sources(root_path: Path) -> Iterator[dict]:
    """
    Parse shcntx_ru and shlang_ru from root_path.
    Yields dicts: {name, full_name, category, description, methods: [...], source}
    """
    shcntx = root_path / "shcntx_ru"
    shlang = root_path / "shlang_ru"

    seen_objects = set()

    # shcntx_ru: objects and methods
    if shcntx.exists():
        # Сначала объекты с methods/ — иначе каталог (catalog259) перекрывает Запрос (Query)
        walk_items = list(_walk_shcntx_objects(shcntx))
        walk_items.sort(key=lambda x: (0 if x[1] else 1, str(x[0])))
        for html_path, methods_dir in walk_items:
            try:
                with open(html_path, encoding="utf-8") as f:
                    soup = BeautifulSoup(f.read(), "lxml")
            except Exception:
                continue

            obj = _parse_object_page(soup, "shcntx_ru")
            if not obj:
                continue

            key = obj.get("full_name") or obj.get("name", "")
            if key in seen_objects:
                continue
            seen_objects.add(key)

            # Enrich methods from method pages
            if methods_dir:
                # Ключ — RU имя (до скобки): "Выполнить" и "Выполнить (Execute)" -> один метод
                def _ru_key(n: str) -> str:
                    return n.split("(")[0].strip() if n else ""

                method_names = {_ru_key(m["name"]): m for m in obj["methods"]}
                for mhtml in methods_dir.glob("*.html"):
                    mdata = _parse_method_page(mhtml, obj.get("full_name", ""), "shcntx_ru")
                    if mdata and mdata.get("name"):
                        ru_key = _ru_key(mdata["name"])
                        if ru_key in method_names:
                            method_names[ru_key].update(mdata)
                            method_names[ru_key]["name"] = ru_key
                        else:
                            method_names[ru_key] = {**mdata, "name": ru_key}
                obj["methods"] = list(method_names.values())

            yield obj

    # shlang_ru: types (def_*) and structures (struct_*)
    if shlang.exists():
        for item in shlang.iterdir():
            if item.is_dir():
                continue
            if item.suffix:
                continue
            name_lower = item.name.lower()
            if name_lower.startswith("def_"):
                parsed = _parse_shlang_item(item, "type", "shlang_ru")
            elif name_lower.startswith("struct_"):
                parsed = _parse_shlang_item(item, "structure", "shlang_ru")
            else:
                continue
            if parsed:
                key = parsed.get("full_name") or parsed.get("name", "")
                if key not in seen_objects:
                    seen_objects.add(key)
                    yield parsed
