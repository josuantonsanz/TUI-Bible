# Content and setup policy

> This policy defines the publication boundary. It is not legal advice and does
> not grant permission to copy, convert, store, or redistribute any data.

## Two kinds of input

1. **Bundled, reviewed data** ships in `startup/` and is tracked in Git with its
   licence recorded in [`THIRD-PARTY-NOTICES.md`](../THIRD-PARTY-NOTICES.md) and
   [`data-provenance.md`](data-provenance.md). Installing it needs no consent
   step because the maintainer has already reviewed the terms.
2. **User-supplied, restricted data** is never bundled and never downloaded. It
   is installed only when the user supplies the file locally and explicitly
   acknowledges the right to use it.

## One-command install of the bundled data

```powershell
uv sync
uv run opengnt setup --full-install
```

This builds a local SQLite database from the reviewed OpenGNT data plus the
bundled lemma glosses, Abbott-Smith dictionary, and Latin translation. It never
downloads anything and deliberately omits embedded NA28 variants. A plain
`opengnt setup` (no options) installs the same bundled set. `--output` chooses a
different database path, `--input-dir` a different source directory, and
`--overwrite` replaces an existing database.

## Restricted opt-in: Biblia de Jerusalén

`startup/spanish_bible.json` is copyrighted and is **not** distributed. A user
who owns a lawful copy may place it in `startup/` and install it explicitly:

```powershell
uv run python scripts/build_translation_json.py --input <your-source> --output startup/spanish_bible.json
uv run opengnt setup --include-bj
```

The command asks a default-no `Y/N` licence question. Answering `N` cancels
setup before any database is written. `build_translation_json.py` is a
code-only converter for a source *you* supply: it downloads nothing, and no
translation is distributed. Do not add the resulting JSON or the source file to
Git.

## NA28 boundary

The bundled OpenGNT CSV contains variant-related fields. The implemented setup
always selects the OpenGNT reading and omits all NA28 variant rows. There is no
public `--include-na28` option: the current schema cannot store editions safely
as independent layers. Do not publish a database produced by the old
destructive NA28 workflow.

## Publishing check

Before the first commit or release, inspect staged and ignored files:

```powershell
git status --short
git status --ignored --short
```

Confirm that `startup/spanish_bible.json`, databases, settings, backups, and
secrets are ignored, and that every other tracked `startup/` file appears in the
provenance register.
