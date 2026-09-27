"""Convert a local verse-translation source into the application's JSON shape.

The application imports verse translations from a structure like::

    {
      "40": {
        "book_name": "Mateo",
        "chapters": {"1": {"1": "text", ...}, ...}
      },
      ...
    }

This module normalises a source file into that shape. The bundled source is a
pickle (``startup/bibliaEsp.pk``) of the form::

    {
      "<book name>": {
        "abreviacion": "<abbr>",
        "chapters": [{"verses": {"1": "text", ...}}, ...]
      },
      ...
    }

but any source with the same structure works, in pickle or JSON form.
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any

from opengnt_interface.bible_books import ES_BOOK_NAMES

# Source book identifiers (abbreviations and canonical names, lower-cased and
# stripped) mapped to the project's New Testament book numbers.
SOURCE_BOOK_IDS: dict[str, int] = {
    "mat": 40, "mt": 40, "mrc": 41, "mar": 41, "mc": 41, "mr": 41,
    "luc": 42, "lc": 42, "jua": 43, "jn": 43, "hec": 44, "hch": 44,
    "rom": 45, "ro": 45, "1cor": 46, "1co": 46, "2cor": 47, "2co": 47,
    "gal": 48, "efes": 49, "ef": 49, "flp": 50, "fili": 50, "fil": 50,
    "col": 51, "1tes": 52, "1ts": 52, "2tes": 53, "2ts": 53,
    "1tim": 54, "1ti": 54, "2tim": 55, "2ti": 55, "tit": 56, "ti": 56,
    "filem": 57, "film": 57, "flm": 57, "heb": 58, "sant": 59, "stg": 59,
    "1ped": 60, "1pe": 60, "1p": 60, "2ped": 61, "2pe": 61, "2p": 61,
    "1jn": 62, "2jn": 63, "3jn": 64, "jud": 65, "apoc": 66, "apo": 66, "ap": 66,
    "mateo": 40, "marcos": 41, "lucas": 42, "juan": 43, "hechos": 44,
    "romanos": 45, "i corintios": 46, "ii corintios": 47, "gálatas": 48,
    "galatas": 48, "efesios": 49, "filipenses": 50, "colosenses": 51,
    "i tesalonicenses": 52, "ii tesalonicenses": 53, "i timoteo": 54,
    "ii timoteo": 55, "tito": 56, "filemon": 57, "filemón": 57,
    "hebreos": 58, "santiago": 59, "i pedro": 60, "ii pedro": 61,
    "i juan": 62, "ii juan": 63, "iii juan": 64, "judas": 65, "apocalipsis": 66,
}

PICKLE_SUFFIXES = {".pk", ".pickle", ".pkl"}


def infer_format(path: Path) -> str:
    """Return ``"pickle"`` or ``"json"`` based on the file extension."""
    return "pickle" if path.suffix.lower() in PICKLE_SUFFIXES else "json"


def _book_number(entry_key: str, entry: dict[str, Any]) -> int | None:
    for candidate in (entry.get("abreviacion"), entry_key):
        if not candidate:
            continue
        number = SOURCE_BOOK_IDS.get(str(candidate).strip().lower())
        if number is not None:
            return number
    return None


def _chapters_from_source(entry: dict[str, Any]) -> dict[str, dict[str, str]]:
    chapters: dict[str, dict[str, str]] = {}
    for chapter_index, chapter in enumerate(entry.get("chapters", []), start=1):
        verses = {str(number): text for number, text in chapter.get("verses", {}).items()}
        chapters[str(chapter_index)] = verses
    return chapters


def convert(source: dict[str, Any]) -> dict[str, Any]:
    """Normalise a source mapping into the application's translation shape."""
    result: dict[str, Any] = {}
    for entry_key, entry in source.items():
        if not isinstance(entry, dict) or "chapters" not in entry:
            continue
        number = _book_number(entry_key, entry)
        if number is None or not 40 <= number <= 66:
            continue
        result[str(number)] = {
            "book_name": ES_BOOK_NAMES[number],
            "chapters": _chapters_from_source(entry),
        }
    return dict(sorted(result.items(), key=lambda item: int(item[0])))


def load_source(path: Path, fmt: str) -> dict[str, Any]:
    if fmt == "pickle":
        with path.open("rb") as handle:
            return pickle.load(handle)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_translation_json(source_path: Path, destination: Path, fmt: str | None = None) -> dict[str, Any]:
    """Convert ``source_path`` and write the importer JSON to ``destination``.

    Returns the converted mapping. Raises ``ValueError`` when the source holds
    no New Testament books.
    """
    fmt = fmt or infer_format(source_path)
    result = convert(load_source(source_path, fmt))
    if not result:
        raise ValueError(f"no New Testament books found in {source_path}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    return result
