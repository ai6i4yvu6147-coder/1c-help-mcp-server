# -*- coding: utf-8 -*-
"""Parser for shquery_ru (1C query language help)."""
import re
from pathlib import Path
from bs4 import BeautifulSoup
from typing import Iterator

_SOURCE = "shquery_ru"
_V8HELP_PREFIX = "v8help://SyntaxHelperQueries/"

_OPERATOR_NAMES = frozenset({
    "BETWEEN", "LIKE", "IS_NULL", "JOIN", "INNERJOIN", "LEFTJOIN",
    "RIGHTJOIN", "FULLJOIN", "GROUPING",
})
_LITERAL_NAMES = frozenset({
    "NULL", "TRUE", "FALSE", "Undefined", "Parameters", "ValueList",
})
_LITERAL_PREFIX = "Lit"


def _extract_text(el) -> str:
    if el is None:
        return ""
    return el.get_text(separator=" ", strip=True) if hasattr(el, "get_text") else str(el)


def _topic_id_from_path(path: Path) -> str:
    return path.stem if path.suffix else path.name


def _classify_category(topic_id: str) -> str:
    if topic_id.startswith("KeyWords"):
        return "query_keyword"
    if topic_id.endswith("Statement") or topic_id.endswith("Section"):
        return "query_statement"
    if (
        topic_id.startswith("Operation")
        or topic_id.startswith("CompareB")
        or topic_id in _OPERATOR_NAMES
    ):
        return "query_operator"
    if topic_id.startswith(_LITERAL_PREFIX) or topic_id in _LITERAL_NAMES:
        return "query_literal"
    if topic_id.endswith(".html") or "." in topic_id:
        return "query_article"
    if Path(topic_id).suffix == ".html":
        return "query_article"
    # extensionless articles like root - handled by suffix check on file
    return "query_function"


def _classify_category_from_file(path: Path) -> str:
    topic_id = _topic_id_from_path(path)
    if path.suffix.lower() == ".html":
        return "query_article"
    return _classify_category(topic_id)


def _parse_title_names(title: str, topic_id: str, category: str) -> tuple[str, str]:
    """Return (name, full_name) for lookup."""
    title = title.strip()
    if not title:
        return topic_id, topic_id

    patterns = [
        (r"^Функция\s+(\S+?)(?:\s*\(([^)]+)\))?\s*$", 1, 2),
        (r"^Агрегатная функция\s+(\S+)\s*$", 1, None),
        (r"^Ключевое слово\s+(\S+)\s*$", 1, None),
        (r"^Предложение\s+(\S+)\s*$", 1, None),
        (r"^Оператор\s+(.+?)\s*$", 1, None),
        (r"^Секция\s+(.+?)\s*$", 1, None),
    ]
    for pattern, name_grp, en_grp in patterns:
        m = re.match(pattern, title, re.IGNORECASE)
        if m:
            name = m.group(name_grp).strip()
            en_name = m.group(en_grp).strip() if en_grp and m.lastindex >= en_grp and m.group(en_grp) else ""
            full_name = en_name or topic_id
            return name, full_name

    if category == "query_article":
        return topic_id, title
    # fallback: last word uppercase token or topic_id
    tokens = title.split()
    if tokens:
        last = tokens[-1].strip(".,;")
        if last.isupper() or re.match(r"^[А-ЯЁA-Z]", last):
            return last, topic_id
    return topic_id, title


def _extract_see_also(soup: BeautifulSoup) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if not href.startswith(_V8HELP_PREFIX):
            continue
        ref = href[len(_V8HELP_PREFIX):].strip()
        if ref.endswith(".html"):
            ref = ref[:-5]
        if ref and ref not in seen:
            seen.add(ref)
            refs.append(ref)
    return refs


def _extract_signature(soup: BeautifulSoup, title: str) -> str:
    pre = soup.find("pre")
    if pre:
        return _extract_text(pre)[:2000]

    for strong in soup.find_all("strong"):
        text = _extract_text(strong)
        if "&lt;" in str(strong) or "<" in text or len(text) > 10:
            if any(kw in text.upper() for kw in ("ВЫБРАТЬ", "ГДЕ", "ИЗ", "СГРУППИРОВАТЬ", "ОБЪЕДИНИТЬ")):
                return text[:2000]
            if "&lt;" in str(strong):
                return text[:2000]

    blockquote = soup.find("blockquote")
    if blockquote:
        btext = _extract_text(blockquote)
        if btext and ("|" in btext or "&lt;" in str(blockquote) or "<" in btext[:50]):
            return btext[:2000]

    return ""


def _extract_example(soup: BeautifulSoup) -> str:
    for h4 in soup.find_all("h4"):
        if "пример" not in _extract_text(h4).lower():
            continue
        parts: list[str] = []
        for sib in h4.next_siblings:
            if getattr(sib, "name", None) == "h4":
                break
            if getattr(sib, "name", None) == "blockquote":
                for font in sib.find_all("font", face=re.compile("Courier", re.I)):
                    t = _extract_text(font)
                    if t:
                        parts.append(t)
                if not parts:
                    t = _extract_text(sib)
                    if t and "результат" not in t.lower():
                        parts.append(t)
        if parts:
            return "\n".join(parts)[:3000]
    return ""


def _extract_description(soup: BeautifulSoup, title: str, example: str) -> str:
    parts: list[str] = []
    in_example = False
    for el in soup.find_all(["p", "h4"]):
        if el.name == "h4":
            label = _extract_text(el).lower()
            if "пример" in label or "результат" in label:
                in_example = True
            continue
        if in_example:
            continue
        text = _extract_text(el)
        if not text or text == title:
            continue
        if "см. также" in text.lower():
            continue
        parts.append(text)
    return " ".join(parts)[:3000]


def _kind_for_category(category: str) -> str:
    return {
        "query_keyword": "QueryKeyword",
        "query_function": "QueryFunction",
        "query_statement": "QueryStatement",
        "query_operator": "QueryOperator",
        "query_literal": "QueryLiteral",
        "query_article": "QueryArticle",
    }.get(category, "QueryTopic")


def _parse_query_file(path: Path) -> dict | None:
    topic_id = _topic_id_from_path(path)
    category = _classify_category_from_file(path)

    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    if not raw.strip() or "<h1" not in raw.lower():
        return None

    soup = BeautifulSoup(raw, "lxml")
    h1 = soup.find("h1")
    if not h1:
        return None

    title = _extract_text(h1)
    if not title or len(title) < 2:
        return None

    name, full_name = _parse_title_names(title, topic_id, category)
    signature = _extract_signature(soup, title)
    example = _extract_example(soup)
    description = _extract_description(soup, title, example)
    see_also = _extract_see_also(soup)

    if not description and not signature and category != "query_article":
        # hub/list pages may have only links
        if not soup.find("ul") and not soup.find("table"):
            return None

    method = {
        "name": name,
        "kind": _kind_for_category(category),
        "signature": signature or None,
        "params": [{"see_also": see_also}] if see_also else [],
        "returns": None,
        "description": description or title,
        "example": example or None,
        "source": _SOURCE,
    }

    return {
        "name": name,
        "full_name": full_name,
        "parent_name": topic_id,
        "category": category,
        "description": description or title,
        "methods": [method],
        "source": _SOURCE,
        "title": title,
    }


def parse_query_sources(root_path: Path) -> Iterator[dict]:
    """
    Parse shquery_ru from root_path.
    Yields dicts compatible with help_parser/importer format.
    """
    shquery = root_path / "shquery_ru"
    if not shquery.exists():
        return

    seen: set[str] = set()
    files = sorted(
        [p for p in shquery.iterdir() if p.is_file() and not p.name.startswith("__")],
        key=lambda p: p.name.lower(),
    )

    for path in files:
        topic_id = _topic_id_from_path(path)
        if topic_id in seen:
            continue

        parsed = _parse_query_file(path)
        if not parsed:
            continue

        seen.add(topic_id)
        yield parsed
