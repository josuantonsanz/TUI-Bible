# Content and setup policy

> This policy defines the publication boundary. It is not legal advice and does
> not grant permission to copy, convert, store, or redistribute any data.

## Two kinds of input

1. **Bundled data** ships in `startup/` and is tracked in Git with its source
   recorded in [`THIRD-PARTY-NOTICES.md`](../THIRD-PARTY-NOTICES.md) and
   [`data-provenance.md`](data-provenance.md). This now includes the Spanish
   *Biblia de Jerusalén* source `startup/bibliaEsp.pk`.
2. **User-supplied data** is never downloaded. `scripts/build_translation_json.py`
   converts a source *you* provide into the importer JSON shape. You are
   responsible for having the rights to whatever you feed it.

## One-command install of the bundled data

```powershell
uv sync
uv run opengnt setup --full-install
```

This builds a local SQLite database from the OpenGNT data plus the bundled
lemma glosses, Abbott-Smith dictionary, Latin translation, the Spanish
translation derived from `startup/bibliaEsp.pk`, and the NA28 readings embedded
in the OpenGNT variant field, which become the primary Greek text. It never
downloads anything. A plain `opengnt setup` (no options) installs the bundled
translations but leaves the Greek text as OpenGNT with no NA28 rows.
`--output` chooses a different database path, `--input-dir` a different source
directory, and `--overwrite` replaces an existing database.

## Biblia de Jerusalén

`startup/bibliaEsp.pk` is the single bundled source for the Spanish translation.
Setup converts it to the importer JSON in a temporary directory while it runs,
so the derived `startup/spanish_bible.json` is a throwaway artifact and is
ignored by Git.

```powershell
uv run opengnt setup --include-bj
```

To inspect a converted copy, rebuild it explicitly:

```powershell
uv run python scripts/build_translation_json.py --input startup/bibliaEsp.pk --output startup/spanish_bible.json
```

Rights in the *Biblia de Jerusalén* text remain with its publishers. Using,
converting, or redistributing it is the responsibility of whoever does so.

## NA28 readings

The bundled OpenGNT CSV carries the NA28 reading for each word that differs from
it, in the `〔Note｜Mvar｜...〕` field. `--full-install` (or `--include-na28` on
its own) reads that field and builds the NA28 text:

```powershell
uv run opengnt setup --include-na28
```

For every word marked `＊` (differs from NA28) or `＝` (orthographic difference
only), setup replaces the main word with the NA28 reading and stores the
original OpenGNT reading in the `variants` table with `source='OpenGNT'`. The
provenance manifest records `primary_variant: "na28"` and
`na28_variants_installed: true`. Plain `setup` keeps the OpenGNT reading and
inserts no variant rows.

Rights in the NA28 text remain with its publishers. Installing it is the
responsibility of whoever runs the command. The separate `opengnt import-data`
command also accepts `--variant-mode na28` for the same behaviour.

## Publishing check

Before the first commit or release, inspect staged and ignored files:

```powershell
git status --short
git status --ignored --short
```

Confirm that `startup/bibliaEsp.pk` and the other bundled inputs are tracked,
while `startup/spanish_bible.json`, databases, settings, backups, and secrets
are ignored.
