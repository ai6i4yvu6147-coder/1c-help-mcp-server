# -*- coding: utf-8 -*-
"""Test tools with existing DB."""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.tools import HelpTools

t = HelpTools("databases")
print("Versions:", t.list_versions())
r = t.get_syntax("Запрос.Выполнить")
print("get_syntax Запрос.Выполнить:", json.dumps(r, ensure_ascii=False, indent=2) if r else None)
r2 = t.get_syntax("Сообщить")
print("get_syntax Сообщить:", "OK" if r2 else "FAIL")
print("search_syntax:", len(t.search_syntax("Выполнить")), "results")
r3 = t.get_object_api("Запрос")
print("get_object_api Запрос:", len(r3.get("methods", [])), "methods" if r3 else "FAIL")
r4 = t.list_syntax(category="object")
print("list_syntax object:", len(r4 or []), "items")
r5 = t.get_syntax("Строка")
print("get_syntax Строка:", "text=" + (r5["text"][:60] + "..." if r5 and len(r5.get("text", "")) > 60 else (r5["text"] or "")) if r5 else "FAIL")
r6 = t.get_syntax("Если")
print("get_syntax Если:", "signature=" + str(r6.get("structured", {}).get("signature", ""))[:50] if r6 else "FAIL")
