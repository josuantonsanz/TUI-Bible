import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent

_spec = importlib.util.spec_from_file_location(
    "build_translation_json", ROOT / "scripts" / "build_translation_json.py"
)
build_translation_json = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_translation_json)


def test_convert_maps_books_and_drops_non_new_testament():
    source = {
        " Mateo": {"abreviacion": "mat", "chapters": [{"verses": {"1": "uno", "2": "dos"}}]},
        "I Corintios": {"abreviacion": "1cor", "chapters": [{"verses": {"1": "uno"}}]},
        "Génesis": {"abreviacion": "gen", "chapters": [{"verses": {"1": "inicio"}}]},
        "Apocalipsis": {"abreviacion": "apoc", "chapters": [{"verses": {"1": "alfa"}}]},
    }

    result = build_translation_json.convert(source)

    assert list(result) == ["40", "46", "66"]
    assert result["40"]["book_name"] == "Mateo"
    assert result["40"]["chapters"] == {"1": {"1": "uno", "2": "dos"}}
    assert result["46"]["book_name"] == "1 Corintios"
    assert "Génesis" not in json.dumps(result, ensure_ascii=False)


def test_convert_ignores_entries_without_chapters():
    assert build_translation_json.convert({"Mateo": {"abreviacion": "mat"}}) == {}
