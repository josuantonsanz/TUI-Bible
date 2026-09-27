# OpenGNT Interface

OpenGNT Interface is an early-stage, keyboard-driven terminal application for
studying and annotating the Greek New Testament. Its primary interface is a
[Textual](https://textual.textualize.io/) TUI with interlinear display,
morphology and gloss fields, annotations, concordance/reference search, and an
optional local dictionary.

> **Publication status — work in progress.** The application code is released
> under the MIT licence. The bundled Greek text and reference data keep their
> own licences (the OpenGNT data is CC BY-SA 4.0); see
> [third-party notices](THIRD-PARTY-NOTICES.md).

## Install and run

[`uv`](https://docs.astral.sh/uv/) is the supported installer. From a clone:

```powershell
uv sync
uv run opengnt setup --full-install
uv run opengnt-tui
```

`setup --full-install` is the one-command build. It imports the bundled
[OpenGNT](https://github.com/eliranwong/OpenGNT) reading plus the bundled lemma
glosses, Abbott-Smith dictionary, Latin translation, the Biblia de Jerusalén
translation, and the NA28 readings embedded in the OpenGNT variant field, which
become the primary Greek text. It never downloads anything.

The mutable data directory is written outside the checkout by default:

- Windows: `%LOCALAPPDATA%\opengnt-interface`
- macOS: `~/Library/Application Support/opengnt-interface`
- Linux: `${XDG_DATA_HOME:-~/.local/share}/opengnt-interface`

Set `OPENGNT_DATA_DIR` to choose another directory. The command creates
`opengnt.db` and a `provenance.json` manifest with input checksums next to it.

### Options

| Command | Result |
| --- | --- |
| `opengnt setup` | Bundled translations (lemma glosses, dictionary, Latin, Biblia de Jerusalén), leaving the Greek text as OpenGNT without NA28 variants. |
| `opengnt setup --full-install` | Everything in `setup` plus the embedded NA28 readings, activated as the primary Greek text. |
| `opengnt setup --include-lemma-glosses` | Bundled Spanish lemma glosses only. |
| `opengnt setup --include-dictionary` | Bundled Abbott-Smith dictionary only. |
| `opengnt setup --include-latin` | Bundled Latin translation only. |
| `opengnt setup --include-bj` | Bundled Biblia de Jerusalén translation only (built from `startup/bibliaEsp.pk`). |
| `opengnt setup --include-na28` | Install the embedded NA28 readings only, activated as the primary Greek text. |
| `opengnt setup --output <path>` | Write the database to a specific file. |
| `opengnt setup --overwrite` | Replace an existing database. |

`--include-bj` builds the Spanish translation from the bundled
`startup/bibliaEsp.pk` pickle while setup runs. The derived JSON is written to a
temporary directory, so only the single source file is tracked. You can still
convert a source you supply yourself with
[`scripts/build_translation_json.py`](scripts/build_translation_json.py) (see
[content and setup policy](docs/restricted-content-setup.md)).

`--include-na28` reads the NA28 reading recorded in the OpenGNT variant field
and replaces the main word with it, keeping the original OpenGNT reading in the
`variants` table. `--full-install` turns it on. Plain `setup` leaves the Greek
text as OpenGNT.

## Development checks

```powershell
uv run pytest -q
uv run opengnt --help
```

The tests use synthetic fixtures and do not require a working database.

## Documentation

- [Startup data and provenance](startup/README.md)
- [Third-party notices](THIRD-PARTY-NOTICES.md)
- [Data provenance and distribution decisions](docs/data-provenance.md)
- [Content and setup policy](docs/restricted-content-setup.md)
- [Historical reconstruction notes](from-scratch.md)
- [Architecture notes](bible-project-architecture.md)

## Contributing and publication

Do not add data, PDFs, database files, keys, or generated exports without a
documented source, licence, attribution requirement, and explicit inclusion
decision in the provenance register. Do not force-add ignored assets.
