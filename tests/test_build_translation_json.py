import importlib.util
import json
import pickle
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


def test_infer_format_recognises_pickles_and_json(tmp_path):
    assert build_translation_json.infer_format(tmp_path / "bibliaEsp.pk") == "pickle"
    assert build_translation_json.infer_format(tmp_path / "bibliaEsp.pkl") == "pickle"
    assert build_translation_json.infer_format(tmp_path / "bible.json") == "json"


def test_write_translation_json_reads_a_pickle(tmp_path):
    source = tmp_path / "bibliaEsp.pk"
    source.write_bytes(
        pickle.dumps(
            {
                " Mateo": {"abreviacion": "mat", "chapters": [{"verses": {"1": "uno"}}]},
                "Génesis": {"abreviacion": "gen", "chapters": [{"verses": {"1": "inicio"}}]},
            }
        )
    )
    destination = tmp_path / "out" / "spanish_bible.json"

    result = build_translation_json.write_translation_json(source, destination)

    assert list(result) == ["40"]
    assert json.loads(destination.read_text(encoding="utf-8")) == result


def test_write_translation_json_rejects_sources_without_new_testament(tmp_path):
    source = tmp_path / "bible.json"
    source.write_text(json.dumps({"Génesis": {"chapters": [{"verses": {"1": "inicio"}}]}}), encoding="utf-8")

    import pytest

    with pytest.raises(ValueError):
        build_translation_json.write_translation_json(source, tmp_path / "out.json")
