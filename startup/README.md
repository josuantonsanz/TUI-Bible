# Bundled startup data

This directory ships the source files that `opengnt setup` imports into a local
SQLite database. They are tracked in Git on purpose so that a fresh clone can
build a complete installation with a single command:

```powershell
uv sync
uv run opengnt setup --full-install
```

Nothing here is downloaded at install time. Each file keeps its own licence;
the full attribution is in [`THIRD-PARTY-NOTICES.md`](../THIRD-PARTY-NOTICES.md)
and the working register in [`docs/data-provenance.md`](../docs/data-provenance.md).

## Files

| Filename | Setup option | Source | Licence |
| --- | --- | --- | --- |
| `OpenGNT_version3_3.csv` | always required | [OpenGNT Project](https://github.com/eliranwong/OpenGNT) (Eliran Wong), v3.3 (2018) | CC BY-SA 4.0 |
| `OpenGNT_morphology_Spanish.csv` | always required | OpenGNT Project, `OpenGNT_morphology_Spanish.csv.zip` | CC BY-SA 4.0 |
| `GK_lemma_SpanishGloss.csv` | `--include-lemma-glosses` | Spanish derivative of OpenGNT `Glossary/GK_lemma_EnglishGloss.csv` | CC BY-SA 4.0 |
| `abbotsmith.json` | `--include-dictionary` | Abbott-Smith (1922) via the [Logeion](https://logeion.uchicago.edu/) API | Public-domain text; digitisation terms under review |
| `latin_vulgate.json` | `--include-latin` | Latin Vulgate (Clementine), retrieved from [sacred-texts.com](https://sacred-texts.com/bib/vul/) | Public domain |

`setup` copies the dictionary only to the local application-data path
`<data-dir>/abbotsmith/dictionary.json`; it is not installed as a package asset.
It creates `<data-dir>/opengnt.db` and a neighbouring `provenance.json` manifest
by default. Set `OPENGNT_DATA_DIR` to choose another local data directory.

## Restricted material (not bundled)

`spanish_bible.json` is a *Biblia de Jerusalén*-derived Spanish text. It is
copyrighted, is **not** redistributed here, and is ignored by Git. If you own a
lawful copy you can place it in this directory and install it explicitly:

```powershell
uv run opengnt setup --include-bj --acknowledge-local-data-rights
```

See [`docs/restricted-content-setup.md`](../docs/restricted-content-setup.md).
