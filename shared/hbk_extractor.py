# -*- coding: utf-8 -*-
"""Извлечение справки 1С из архивов .hbk.

Файл .hbk — это контейнер 1С (формат v8): заголовок 16 байт, затем блоки
с текстовым заголовком ``\\r\\n%08x %08x %08x \\r\\n`` (размер данных, размер
страницы, адрес следующей страницы). Корневой блок по смещению 16 — оглавление:
записи по 12 байт ``(адрес_атрибутов, адрес_данных, 0x7fffffff)``.

Внутри контейнера справки лежит элемент ``FileStorage`` — это обычный ZIP
с HTML-страницами (``objects/*.html`` для shcntx, ``def_*``/``struct_*`` для
shlang, темы языка запросов для shquery). Именно его мы и распаковываем, чтобы
дальше отдать существующим парсерам (help_parser / query_parser).
"""
import io
import struct
import zipfile
from pathlib import Path

# Ядро справки Синтакс-помощника: объекты/методы (API), типы и конструкции
# языка, язык запросов. Только русские версии — файлы *_root.hbk английские.
HELP_SOURCES = ("shcntx_ru", "shlang_ru", "shquery_ru")

_FREE_PAGE = 0x7FFFFFFF
_BLOCK_HEADER_LEN = 31


def _read_block(f, offset: int) -> bytes:
    """Прочитать поток данных v8-контейнера, начиная с блока по смещению offset."""
    f.seek(offset)
    header = f.read(_BLOCK_HEADER_LEN)
    if header[:2] != b"\r\n":
        raise ValueError(f"Не блок v8-контейнера по смещению {offset}")
    data_size = int(header[2:10], 16)
    page_size = int(header[11:19], 16)
    next_addr = int(header[20:28], 16)

    out = bytearray(f.read(page_size))
    while next_addr != _FREE_PAGE and len(out) < data_size:
        f.seek(next_addr)
        header = f.read(_BLOCK_HEADER_LEN)
        page_size = int(header[11:19], 16)
        next_addr = int(header[20:28], 16)
        out += f.read(page_size)
    return bytes(out[:data_size])


def _read_elements(f) -> dict[str, bytes]:
    """Вернуть {имя_элемента: данные} для открытого файла v8-контейнера."""
    f.seek(0)
    f.read(16)  # заголовок файла — не используется, размеры берём из блоков
    toc = _read_block(f, 16)
    elements: dict[str, bytes] = {}
    for pos in range(0, len(toc) - (len(toc) % 12), 12):
        attr_addr, data_addr, _ = struct.unpack_from("<III", toc, pos)
        attr = _read_block(f, attr_addr)
        # Атрибуты: 20 байт служебных (даты), затем имя в UTF-16LE.
        name = attr[20:].decode("utf-16-le", "replace").rstrip("\x00")
        data = _read_block(f, data_addr) if data_addr != _FREE_PAGE else b""
        elements[name] = data
    return elements


def is_hbk_archive(path: Path) -> bool:
    """True, если файл похож на контейнер справки 1С (сигнатура блока v8)."""
    try:
        with open(path, "rb") as f:
            f.seek(16)
            return f.read(2) == b"\r\n"
    except OSError:
        return False


def extract_hbk(hbk_path: Path, target_dir: Path) -> int:
    """Распаковать HTML-страницы из одного .hbk в target_dir.

    Возвращает число извлечённых записей. Бросает ValueError, если это не
    контейнер справки (нет элемента FileStorage).
    """
    with open(hbk_path, "rb") as f:
        elements = _read_elements(f)

    storage = elements.get("FileStorage")
    if not storage:
        raise ValueError(f"В {hbk_path.name} нет элемента FileStorage — это не справка 1С")

    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(storage)) as z:
        z.extractall(target_dir)
        return len(z.namelist())


def find_help_archives(source_dir: Path) -> list[str]:
    """Список имён ядровых .hbk (без расширения), присутствующих в папке."""
    return [name for name in HELP_SOURCES if (source_dir / f"{name}.hbk").exists()]


def extract_help_folder(source_dir: Path, target_dir: Path) -> dict[str, int]:
    """Распаковать ядровые архивы (shcntx_ru, shlang_ru, shquery_ru) из папки.

    Каждый архив уходит в target_dir/<имя>/. Возвращает {имя: число_записей}.
    """
    result: dict[str, int] = {}
    for name in find_help_archives(source_dir):
        result[name] = extract_hbk(source_dir / f"{name}.hbk", target_dir / name)
    return result
