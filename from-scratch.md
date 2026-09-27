# Reconstruction and historical-build notes

The supported bootstrap is the `setup` command documented in the root
[README](README.md) and [`startup/README.md`](startup/README.md). It creates a
new local database from the bundled inputs and uses the OpenGNT reading by
default; `--full-install` or `--include-na28` also installs the embedded NA28
readings.

This document preserves the historical context only.

## Input files

The working tree used these files, now tracked in `startup/`:

| Filename | Role | Distribution |
| --- | --- | --- |
| `OpenGNT_version3_3.csv` | Main word/text/metadata import; contains variant fields. | Bundled, CC BY-SA 4.0. |
| `OpenGNT_morphology_Spanish.csv` | RMAC morphology mapping. | Bundled, CC BY-SA 4.0. |
| `GK_lemma_SpanishGloss.csv` | Spanish lemma glosses. | Bundled, CC BY-SA 4.0 derivative. |
| `abbotsmith.json` | Abbott-Smith lookup resource, extracted via the Logeion API. | Bundled; digitisation terms under review. |
| `latin_vulgate.json` | Latin Vulgate verse translation. | Bundled, public domain. |
| `bibliaEsp.pk` | Biblia de Jerusalén Spanish source pickle. | Bundled; converted to JSON during setup. |

## What was repaired

- One user-data resolver is now used by the CLI, Textual TUI, settings, backup
  default, and local dictionary path.
- `setup` builds in a temporary directory and does not overwrite a database
  unless explicitly asked.
- The SQLAlchemy `Word` model now declares the four fields the importer writes:
  `fonetica`, `it_translation`, `lt_translation`, and `st_translation`.
- A plain import excludes NA28 variant rows instead of retaining them as an
  implicit side effect; `--full-install`/`--include-na28` installs and activates
  them explicitly.
- The unmaintained `scripts/` collection, legacy prompt-toolkit TUI, and
  dictionary download utilities were removed. Their code was not imported by
  the supported CLI or Textual application; many tools used a root database,
  personal paths, AGNT material, remote scraping, or destructive migrations.
- `setup --full-install` and the `opengnt` / `opengnt-tui` console scripts make a
  fresh clone usable in one step.

## Remaining limitations

Optional translations still use the historical `spanish_text` / `latin_text`
schema rather than a generic edition model, and the Abbott-Smith digitisation
terms still need confirmation. See [`plan.md`](plan.md) for the open items and
[`docs/data-provenance.md`](docs/data-provenance.md) for the asset register.
