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
glosses, Abbott-Smith dictionary, and Latin translation, and deliberately omits
embedded NA28 variants. It never downloads anything.

The mutable data directory is written outside the checkout by default:

- Windows: `%LOCALAPPDATA%\opengnt-interface`
- macOS: `~/Library/Application Support/opengnt-interface`
- Linux: `${XDG_DATA_HOME:-~/.local/share}/opengnt-interface`

Set `OPENGNT_DATA_DIR` to choose another directory. The command creates
`opengnt.db` and a `provenance.json` manifest with input checksums next to it.

### Options

| Command | Result |
| --- | --- |
| `opengnt setup` | Same as `--full-install` (the reviewed, bundled set). |
| `opengnt setup --full-install` | Install every bundled resource in one step. |
| `opengnt setup --include-lemma-glosses` | Bundled Spanish lemma glosses only. |
| `opengnt setup --include-dictionary` | Bundled Abbott-Smith dictionary only. |
| `opengnt setup --include-latin` | Bundled Latin translation only. |
| `opengnt setup --include-bj` | Install a **local** Biblia de Jerusalén JSON that you own (not bundled); asks for a licence confirmation. |
| `opengnt setup --output <path>` | Write the database to a specific file. |
| `opengnt setup --overwrite` | Replace an existing database. |

`--include-bj` asks a single interactive `Y/N` licence question; answering `N`
cancels setup before any database is written. The file is copyrighted and is
not distributed here. If you have a source you are entitled to use, build the
expected JSON locally with [`scripts/build_translation_json.py`](scripts/build_translation_json.py)
(see [restricted-content policy](docs/restricted-content-setup.md)).

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
