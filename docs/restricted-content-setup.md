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
lemma glosses, Abbott-Smith dictionary, Latin translation, and the Spanish
translation derived from `startup/bibliaEsp.pk`. It never downloads anything and
deliberately omits embedded NA28 variants. A plain `opengnt setup` (no options)
installs the same bundled set. `--output` chooses a different database path,
`--input-dir` a different source directory, and `--overwrite` replaces an
existing database.

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

Confirm that `startup/bibliaEsp.pk` and the other bundled inputs are tracked,
while `startup/spanish_bible.json`, databases, settings, backups, and secrets
are ignored.
