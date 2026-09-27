import csv
import sqlite3
from pathlib import Path

from opengnt_interface.importers import OpenGNTImporter


def write_fixture_inputs(directory: Path) -> tuple[Path, Path]:
    main_csv = directory / "OpenGNT_version3_3.csv"
    morph_csv = directory / "OpenGNT_morphology_Spanish.csv"
    fields = [
        "OGNTsort", "TANTTsort", "FEATURESsort1", "LevinsohnClauseID", "OTquotation",
        "〔Book｜Chapter｜Verse〕", "〔OGNTk｜OGNTu｜OGNTa｜lexeme｜rmac｜sn〕",
        "〔BDAGentry｜EDNTentry｜MounceEntry｜GoodrickKohlenbergerNumbers｜LN-LouwNidaNumbers〕",
        "〔transSBLcap｜transSBL｜modernGreek｜Fonética_Transliteración〕",
        "〔TBESG｜IT｜LT｜ST｜Español〕", "〔PMpWord｜PMfWord〕",
        "〔Note｜Mvar｜Mlexeme｜Mrmac｜Msn｜MTBESG〕",
    ]
    row = {
        "OGNTsort": "40001001001",
        "TANTTsort": "", "FEATURESsort1": "", "LevinsohnClauseID": "", "OTquotation": "",
        "〔Book｜Chapter｜Verse〕": "〔40｜1｜1〕",
        "〔OGNTk｜OGNTu｜OGNTa｜lexeme｜rmac｜sn〕": "〔βίβλος｜βιβλος｜βίβλος｜βίβλος｜N-NSF｜976〕",
        "〔BDAGentry｜EDNTentry｜MounceEntry｜GoodrickKohlenbergerNumbers｜LN-LouwNidaNumbers〕": "〔a｜b｜c｜d｜e〕",
        "〔transSBLcap｜transSBL｜modernGreek｜Fonética_Transliteración〕": "〔Biblos｜biblos｜βίβλος｜vivlos〕",
        "〔TBESG｜IT｜LT｜ST｜Español〕": "〔book｜libro｜liber｜book｜libro〕",
        "〔PMpWord｜PMfWord〕": "〔｜〕",
        # A variant in the fixture verifies that the default setup does not retain NA28 data.
        "〔Note｜Mvar｜Mlexeme｜Mrmac｜Msn｜MTBESG〕": "〔*｜βίβλου｜βίβλος｜N-GSF｜976｜book〕",
    }
    with main_csv.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerow(row)
    with morph_csv.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=["OGNTsort", "RMAC"], delimiter="\t")
        writer.writeheader()
        writer.writerow({"OGNTsort": "40001001001", "RMAC": "N-NSF"})
    return main_csv, morph_csv


def test_fresh_import_matches_declared_schema_and_omits_na28(tmp_path):
    main_csv, morph_csv = write_fixture_inputs(tmp_path)
    database = tmp_path / "opengnt.db"

    stats = OpenGNTImporter(database).run_import(main_csv, morph_csv)

    assert stats.words_imported == 1
    assert stats.variants_created == 0
    with sqlite3.connect(database) as connection:
        word = connection.execute(
            "SELECT fonetica, it_translation, lt_translation, st_translation, rmac FROM words"
        ).fetchone()
        assert word == ("vivlos", "libro", "liber", "book", "N-NSF")
        assert connection.execute("SELECT COUNT(*) FROM variants").fetchone()[0] == 0
