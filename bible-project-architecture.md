# OpenGNT Interface: project description and architecture

## 1. Purpose, scope, and publication boundary

OpenGNT Interface is an early-stage, local-first application for studying and
annotating the Greek New Testament. Its primary user experience is a
keyboard-driven [Textual](https://textual.textualize.io/) terminal UI. It
presents an interlinear view of a verse and supports word- and lemma-level
Spanish glosses, phrase and verse translations, annotations, concordance,
Greek/translation search, optional Abbott-Smith dictionary lookup, parallel
passages, backups, and experimental stylometric highlighting.

The project is deliberately split into two boundaries:

- **Version-controlled application and reviewed data:** Python source,
  documentation, examples, UI-string translations, synthetic tests, and the
  reviewed datasets bundled under `startup/` (OpenGNT, lemma glosses,
  Abbott-Smith dictionary, Latin Vulgate) with their licences recorded in
  [`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md).
- **User-controlled local installation:** a SQLite database built from the
  bundled data, plus settings, provenance metadata, backups, user edits, and
  any restricted resource the user supplies locally.

This distinction is architectural, not merely an ignore rule. The bundled
assets are documented, licensed, and tracked; anything whose provenance and
terms have not been reviewed must not be downloaded or silently enabled. In
particular, NA28 material, Biblia de Jerusalén (BJ) material, BibleWorks/AGNT
material, personal research files, and all working databases remain outside the
public repository. The application code is MIT-licensed; the bundled data keeps
its own licences.

The provenance register in [`docs/data-provenance.md`](docs/data-provenance.md)
and the operating policy in
[`docs/restricted-content-setup.md`](docs/restricted-content-setup.md) are the
authoritative documentation for this boundary. This document describes the
software architecture; it does not establish rights to any input or output.

## 2. Supported entry points

| Entry point | Command | Role |
| --- | --- | --- |
| Textual TUI | `uv run opengnt-tui` | The only supported terminal UI for study and local editing. |
| CLI | `uv run opengnt --help` | Database setup, inspection, search, exports, verification, and backup commands. |
| One-command install | `uv run opengnt setup --full-install` | Builds a complete local database from the bundled inputs in `startup/`. |
| Restricted opt-in | `uv run opengnt setup --include-bj --acknowledge-local-data-rights` | Installs a user-supplied BJ text that is not bundled. |
| Tests | `uv run pytest -q` | Runs synthetic, data-free tests. |

The former prompt-toolkit UI (`opengnt_interface/tui.py`), the CLI command
that invoked it, its legacy headless test, and the old `scripts/` tree were
removed. Those components had divergent database conventions, destructive or
manual workflows, personal paths, AGNT dependencies, or undocumented scraping
behaviour. `tui_textual.py` is therefore the sole TUI implementation to extend.

When launched as a module, the TUI first checks for the resolved local
database. If none is installed, it exits with setup guidance; it must not create
or open an empty database in the source checkout.

## 3. Repository map

```text
.
├── README.md                         # installation, data policy, quick start
├── LICENSE                           # MIT licence for the application code
├── THIRD-PARTY-NOTICES.md            # bundled data sources and licences
├── bible-project-architecture.md     # this architecture reference
├── docs/
│   ├── data-provenance.md            # asset register and approval process
│   └── restricted-content-setup.md   # content and setup policy
├── startup/                          # bundled, licensed source datasets
│   └── README.md                     # roles, sources, and licences
├── opengnt_interface/
│   ├── tui_textual.py                # Textual app, screens, widgets, interaction flow
│   ├── cli.py                        # Typer command-line application and safe setup
│   ├── importers.py                  # OpenGNT/RMAC and optional lemma-gloss import
│   ├── bible_translation_importer.py # optional Spanish/Latin verse JSON import
│   ├── models.py                     # SQLAlchemy schema declarations
│   ├── repositories.py               # persistence/query operations
│   ├── services.py                   # application/business services and view DTOs
│   ├── paths.py                      # one resolver for mutable local resources
│   ├── config.py                     # persisted TUI display configuration
│   ├── db.py                         # default SQLAlchemy engine/session helper
│   ├── bible_books.py                # NT names, abbreviations, and reference parsing
│   ├── morphology.py                 # RMAC expansion for display
│   ├── asparser.py                   # Abbott-Smith HTML/XML to Rich Text formatter
│   ├── cli_utils.py                  # CLI JSON/CSV/plain-text formatting
│   ├── translations/en.json, es.json # UI messages
│   └── data/parallels.json            # approved parallel-passage references
├── examples/                         # executable, database-mutating service examples
├── tests/                            # synthetic pytest/unittest coverage
├── stylometry-documentation.md       # stylometry model and visual semantics
├── TODO.md                           # unfinished product work
└── pyproject.toml / uv.lock          # Python 3.12+ project and locked dependencies
```

`startup/` contains the reviewed datasets that ship with the project
(`startup/spanish_bible.json` is the one exception: it is restricted and
ignored). The ignore rules also exclude Python environments and caches,
runtime databases and SQLite sidecars, backups, secrets, the local AI-assistant
configuration, and generated output.

## 4. Architectural layers and dependency direction

The application is a local desktop-style system with SQLite as its persistence
boundary. It has no web server, remote service, authentication system, or
network acquisition path in the supported workflow.

```text
Authorised local startup files             Local optional resources
         │                                       │
         └── setup / importers ──────────────────┘
                         │
                         ▼
              SQLite database + provenance.json
                         │
      ┌──────────────────┴──────────────────┐
      ▼                                     ▼
SQLAlchemy models ← repositories ← services / view DTOs
                                         │
                         ┌───────────────┴───────────────┐
                         ▼                               ▼
                    Textual TUI                       Typer CLI
                         │                               │
                  settings.json, backups       JSON / CSV / text / files
```

The intended separation is:

1. **Infrastructure and import:** `paths.py` determines locations;
   `importers.py` and `bible_translation_importer.py` create/populate SQLite.
2. **Data model:** `models.py` is the schema source used to create fresh
   databases.
3. **Repository layer:** `repositories.py` contains SQLAlchemy-backed CRUD and
   lookup operations rather than UI code.
4. **Service layer:** `services.py` combines repositories into translation
   resolution, interlinear data, annotations, dictionary formatting, projects,
   variants, search, concordance, and parallel-passage logic.
5. **Presentation/commands:** `tui_textual.py` consumes the services for an
   interactive application; `cli.py` builds services per command and serializes
   results through `cli_utils.py`.

This is a useful structure, but it is not a strict framework boundary yet:
repositories commit several writes themselves, the TUI directly constructs
repositories/services and performs display-specific processing, and some
features are placeholders or optional-resource probes. New work should retain
the direction above rather than adding direct SQLite access to UI screens.

## 5. Local state and path resolution

`opengnt_interface.paths` is the single supported resolver for mutable state.
It does **not** create directories merely by resolving a path. Set
`OPENGNT_DATA_DIR` to override the base directory, which is useful for a
portable installation and tests.

| Resource | Resolved location |
| --- | --- |
| SQLite database | `<data-dir>/opengnt.db` |
| TUI settings | `<data-dir>/settings.json` |
| Optional dictionary | `<data-dir>/abbotsmith/dictionary.json` |
| Backups | `<data-dir>/backups/` |
| Setup manifest | `<data-dir>/provenance.json` by default |

Without an override, `<data-dir>` is `%LOCALAPPDATA%\opengnt-interface` on
Windows, `~/Library/Application Support/opengnt-interface` on macOS, and
`${XDG_DATA_HOME:-~/.local/share}/opengnt-interface` on Linux.

The CLI can accept an explicit database path where relevant. `setup --output`
uses the requested database path and writes `provenance.json` beside that
output; dictionary installation still uses the resolver's dictionary path.
The legacy convenience module `db.py` creates a module-level SQLAlchemy engine
for the resolved default database, but the supported CLI and TUI generally
create their own engine/session for the target database.

`config.py` persists an `InterlinearConfig` JSON document. It controls
interlinear field visibility, translations, annotations, dictionary panel,
stylometry display, and UI language. Unknown keys in a settings file are
ignored, and an unreadable file falls back to defaults. UI strings are loaded
by the `i18n` singleton from package-local `translations/en.json` and
`translations/es.json`; unavailable keys fall back to English and then the key
itself.

## 6. Database design

### 6.1 Schema ownership and creation

`models.py` defines the SQLAlchemy declarative `Base`. A fresh import calls
`Base.metadata.create_all()` and then adds indexes used by the importer. There
is currently no migration framework: a database created by an older schema is
not automatically upgraded. Before reusing a historical database, inspect it
with `PRAGMA table_info(words);` and compare it with `Word` in `models.py`.

`OpenGNTImporter` additionally creates indexes on word reference, lexeme,
Strong's number, OpenGNT sort order, and variant word ID. SQLite foreign-key
enforcement is enabled by the importer connection.

### 6.2 Entity map

| Area | Tables / model | Responsibility |
| --- | --- | --- |
| Canonical text | `books` / `Book`; `words` / `Word` | New Testament book metadata and one ordered base-text word per location. `words` is unique on `(book_id, chapter, verse, word_order)`. |
| Textual variants | `variants` / `Variant` | Alternate word data tied to a base `Word`. The supported importer currently creates none. |
| Translation overrides | `lemma_translations`, `word_translations`, `phrase_translations`, `verse_translations` | Spanish lemma/word/phrase overrides and fixed Spanish/Latin verse text fields. |
| Annotations | `annotations`, `lemma_annotations` | Word, phrase/passage-capable, verse, and lemma notes with category and export fields. |
| Study projects | `projects`, `project_passages` | Named projects and an ordered list of passage ranges. |

A `Word` stores source sort keys and metadata, book/chapter/verse/order,
accented and unaccented Greek, lexeme, Strong's number, RMAC morphology,
lexicon references, transliterations, base gloss/translation fields,
punctuation, source note, and related variants. In particular, the model now
declares the four fields written by the importer that were previously missing:

- `fonetica`
- `it_translation`
- `lt_translation`
- `st_translation`

The translation tables encode the current prioritisation model:

```text
word-specific Spanish override
    → lemma-wide Spanish override
        → source word.spanish_base
            → "(No translation found)"
```

Phrase translations are independently stored by verse and word-order range;
the current service treats a whole-verse phrase translation as start `1`, end
`999`. `VerseTranslation` has one record per book/chapter/verse and fixed
`spanish_text` and `latin_text` columns. This is a known modelling limitation:
a future edition/resource layer must record edition, source, licence,
attribution, consent, and language rather than conflating text layers in fixed
columns.

## 7. Local bootstrap and import pipeline

### 7.1 Required and optional inputs

The safe, documented bootstrap is `cli setup`. It accepts only files supplied
from a local directory (default `startup/`) and never downloads data.

| Input filename | Used by | Selection |
| --- | --- | --- |
| `OpenGNT_version3_3.csv` | `OpenGNTImporter` | required |
| `OpenGNT_morphology_Spanish.csv` | RMAC mapping keyed by `OGNTsort` | required |
| `GK_lemma_SpanishGloss.csv` | `populate_lemma_translations` | bundled; default |
| `latin_vulgate.json` | `BibleTranslationImporter` | bundled; default |
| `abbotsmith.json` | copied to local dictionary path | bundled; default |
| `spanish_bible.json` | `BibleTranslationImporter` | `--include-bj`; restricted, not bundled |

The bundled resources are selected by default (`setup` and `setup
--full-install` are equivalent); individual `--include-*` flags remain for a
granular install. Because the bundled assets have already been reviewed and
recorded in the provenance register, they need no consent step. The only
resource that requires a command-level `--acknowledge-local-data-rights` flag
and an interactive, default-no `Y/N` confirmation is the restricted
Biblia de Jerusalén text, which the user must supply locally. This is intended
to make restricted resource selection explicit, not to turn the application
into an acquisition mechanism.

### 7.2 Transactional setup flow

```text
validate acknowledgement and input paths
        ↓
validate every selected optional file and collect it for the manifest
        ↓
obtain per-resource confirmations
        ↓
create a temporary directory beside the requested output
        ↓
create schema → populate books → load RMAC → parse/import OpenGNT words
        ↓
optionally import lemma glosses and/or verse JSON translations
        ↓
move the completed temporary database to the output
        ↓
optionally copy dictionary to <data-dir>/abbotsmith/dictionary.json
        ↓
write neighbouring provenance.json with paths, SHA-256 hashes, flags, and time
```

An existing output is refused unless `--overwrite` is supplied. The temporary
build protects the old database when an import fails. `provenance.json` is
local metadata recording the selected input paths/checksums, setup time,
rights acknowledgement, `primary_variant: "opengnt"`, and that NA28 variants
were not installed.

### 7.3 OpenGNT importer behaviour

`OpenGNTImporter` reads both CSV files as tab-delimited data. It parses the
bracketed, pipe-delimited fields in the main CSV; assigns a one-based
`word_order` within each verse; creates the 27 Spanish-named book rows; and
inserts words in batches. The RMAC file is a separate mapping, so its RMAC
value replaces the corresponding main-file value when available. Parsing
problems are collected in `ImportStats.errors` rather than crashing the whole
row pass.

Its defaults are intentionally:

```python
OpenGNTImporter(db_path, primary_variant="opengnt", include_na28=False)
```

Consequently the base word remains the OpenGNT reading and no `variants` row
is inserted, even when the input's variant-related field is populated. The
supported `setup` and `import-data` command paths use this configuration;
`import-data --variant-mode` rejects every value except `opengnt`. The importer
still contains historical NA28-switching code behind `include_na28=True`, but
that is not a supported public workflow and must not be exposed until an
edition-aware design and rights decision exist.

The optional `BibleTranslationImporter` imports JSON verse maps through raw
SQLite and upserts the corresponding Spanish and/or Latin column. The optional
lemma-gloss helper inserts unique `(lemma, spanish_translation)` data from a
tab-delimited three-column file. These mechanisms preserve historical schema
assumptions and should be replaced when translation resources are generalized.

A reported private base import completed with 138,013 words, zero variants, 27
books, and a 40.02 MB database; that result describes a local input set, not a
distributed fixture or a guarantee about another database.

## 8. Repository and service layer

### 8.1 Repositories

`repositories.py` centralizes routine queries and writes:

- `TextRepository` retrieves books, words, verses, passages, lemma
  occurrences, contexts, translations, and searches. It also directly edits,
  reorders, inserts, deletes, and punctuates words.
- `TranslationRepository` reads/writes lemma, word, and phrase translations.
- `AnnotationRepository` handles verse, word, and lemma annotations and the
  replacement-oriented delete helpers.
- `ProjectRepository` creates named projects and ordered passage records.
- `VariantRepository` reads/adds/deletes variants.

Word reordering and insertion carefully use temporary or reverse ordering to
avoid violating the per-verse unique word-order constraint. These are direct,
mutable edits to the local base database, so the TUI editing tools are research
workflows rather than a protected edition-management system.

### 8.2 Services and data returned to views

`services.py` is the aggregation layer. Its most important type is
`InterlinearVerse`, containing a display reference, `InterlinearWord` values,
phrase translations, optional Spanish/Latin verse text, and optional parallel
pericopes. `InterlinearService.get_verse_data()` resolves each word's display
translation and variants, then adds verse-level context. It also provides:

- passage aggregation;
- lemma concordance grouped first by inflection/translation and also by book;
- global search, selecting Greek search when the query contains Greek Unicode
  and otherwise searching custom phrase translations and Spanish verse text;
- optional stylometry data attached by lexeme.

`TranslationService` implements the three-level word-translation precedence
shown above. `AnnotationService` combines a specific word's annotations with
lemma-wide annotations and implements replacement semantics for editor
screens. `VariantService` permits manually tracked variants, although the base
bootstrap does not import NA28 rows. `ProjectService` validates project and
book names before adding a range. `DictionaryService` loads a local JSON map
and uses `AbbottSmithParser` to turn entry HTML/XML into styled Rich text.
`ParallelPassageService` reads a local `parallels.json` when it exists and
matches a verse to its supplied ranges.

`opengnt_interface/data/parallels.json` is an approved, tracked package
resource containing parallel-passage titles and references; the service uses it
when finding related pericopes. Stylometry data remains an optional ignored
local resource. `InterlinearService` and the CLI/TUI tolerate absent optional
resources by returning empty data. The stylometry formulas and intended colours
are documented in [`stylometry-documentation.md`](stylometry-documentation.md).

## 9. Textual TUI

`opengnt_interface.tui_textual` is a self-contained Textual `App` built around
an `OpenGNTState`. On startup that state opens the resolved database, creates a
SQLAlchemy session, wires the repositories/services, loads the optional
dictionary/parallels resources, and requests the selected verse.

### 9.1 Main composition

The main screen contains:

1. a Textual header;
2. a phrase-translation editor;
3. `InterlinearDisplay`, which renders responsive stacks of Greek text, RMAC,
   Strong's number, lemma, and resolved translation;
4. panels for instance annotations, lemma annotations, verse annotations,
   Spanish/Latin verse translations, parallel passages, and an optional
   dictionary preview; and
5. a persistent shortcut menu.

The selected word is reactive. Left/right selects a word; up/down changes
verse. The display responds to visibility settings and can colour words using
available stylometry data. The TUI uses a Flexoki-inspired colour palette.

### 9.2 Screens and workflows

Modal or secondary screens implement help, reference navigation, settings,
annotation editing, word/lemma translation editing, Greek-word editing,
punctuation editing, a Greek edit-tools menu, concordance, dictionary lookup,
and debounced global search. Reference parsing accepts English and Spanish NT
names/abbreviations via `bible_books.py`; display book names follow the chosen
English or Spanish UI language.

The principal keyboard workflows are:

| Area | Actions |
| --- | --- |
| Navigation | arrows for verse/word, `g` to go to a reference, `q` to quit |
| Study | `c` concordance, `d` dictionary, `s` search, `h` help |
| Annotations | `a` word, `A` lemma, `v`/`V` verse |
| Translation | `t` word override, `T` lemma override, `p` phrase editor |
| Greek editing | `Ctrl+E` opens edit/move/insert/delete/punctuation tools |
| Application state | `,` settings and `b` local backup |

The phrase editor saves a whole-verse Spanish phrase translation. The Greek
editing tools update, insert, reorder, or delete records directly in SQLite;
they do not preserve a separate editorial layer. Backups copy the resolved
local database to the resolved backups directory with a timestamp.

The TUI checks for the database in its module entry block before creating
`OpenGNTApp`. It therefore emits an actionable message on a clean clone:

```text
No local database is installed. Run uv run python -m opengnt_interface.cli
setup --acknowledge-local-data-rights after placing authorised inputs in
startup/.
```

## 10. CLI

`cli.py` is a Typer application with Rich output. It normalizes stdout/stderr
to UTF-8 on Windows so Greek diagnostics render safely. Commands that query a
database construct a SQLAlchemy session and service graph through
`_get_services()` and close the session in `finally`.

| Command | Current responsibility |
| --- | --- |
| `setup` | Safe local bootstrap, optional-resource confirmation, atomic output move, manifest. |
| `import-data` | Direct OpenGNT/RMAC import to a requested DB; only `opengnt` variant mode is accepted. |
| `read` | Read one parsed verse as plain text, JSON, or CSV. |
| `word` | Inspect a word ID or return lemma concordance as text/JSON. |
| `search` | Search Greek or Spanish translation text as text/JSON. |
| `dictionary` | Look up a local dictionary entry as stripped text or JSON HTML. |
| `stylometry` | Return raw lexeme/word/reference stylometry JSON when optional data exists. |
| `export` | Export a currently supported single verse to `.json` or `.csv`. |
| `verify` | Report books, words, variants, and a `Juan 1:1` query check. |
| `import-verse-translations` | Directly import supplied Spanish and/or Latin JSON into an existing DB. |
| `backup` | Copy or gzip a timestamped database backup. |

`setup` is the supported private installation route. Direct import and
translation commands exist as low-level local tooling, but do not replace the
provenance/confirmation guarantees of setup. `read` currently parses a
reference but retrieves a single verse despite its range-oriented help text;
`export` similarly reports that broad passage export remains unimplemented.

`cli_utils.py` provides dataclass-aware JSON serialization, CSV flattening,
interlinear plain-text formatting, and concordance text formatting. It is the
right place to improve CLI representations without moving presentation logic
into repositories.

## 11. Reference parsing, morphology, and dictionary formatting

- `bible_books.py` maps NT identifiers 40–66 to English and Spanish standard
  names/abbreviations. It normalizes joined numbers and Roman-number prefixes
  and parses forms such as `John 3:16`, `1 Cor 1,1`, `Mateo 1 1`, a chapter, or
  a book-only reference.
- `morphology.py` expands common Robinson Morphological Analysis Codes (RMAC)
  into the project's concise Spanish labels, for example
  `V-PAI-3S → v, pres, act, ind, 3ª pers, s`. It is used in the TUI and
  concordance, while the original code remains in the database.
- `asparser.py` uses BeautifulSoup and Rich to format local Abbott-Smith entry
  markup. It understands entry headers, Strong's references, paragraphs,
  italic/bold text, references, foreign-language fragments, etymologies, and
  Septuagint segments. The dictionary is optional; an absent dictionary must
  leave the rest of the TUI usable.

## 12. Testing, examples, and validation status

The test suite intentionally uses synthetic inputs and needs neither ignored
startup assets nor a working database. It currently covers:

- CLI help, local-rights prompt behaviour, and a clean failure when no database
  exists;
- a fresh synthetic tab-delimited import, including the four repaired `Word`
  fields and the default of zero imported variants;
- English/Spanish UI-string loading and fallback; and
- representative noun, adjective, article, verb, conjunction, and preposition
  morphology expansions.

The recorded command is:

```powershell
uv run pytest -q
```

The last reported result was **15 passed**. Examples in `examples/` demonstrate
annotation, service/project, and manual-variant APIs against a local database.
They are illustrative scripts, not isolated tests: the service and annotation
examples persist changes, while the variant example attempts to roll back its
demonstration transaction. Run them only on a disposable or backed-up local
database.

## 13. Current limitations and planned direction

The repository is an active work in progress. Important limitations are
explicit rather than hidden:

1. **Data rights follow-ups:** the Abbott-Smith digitisation terms still need
   confirmation, and the external translation model (BJ) remains user-supplied.
2. **Edition model:** the current schema cannot safely represent independent
   editions or critical apparatus. NA28/NA29/USB6 support must wait for
   edition-aware, non-destructive storage with source, rights, attribution, and
   consent metadata.
3. **Translations:** Spanish and Latin verse fields are fixed historical
   columns. User-installable, resource-aware translations need a generalized
   model.
4. **Feature completeness:** project management and export are incomplete;
   broad range export is not implemented; search/concordance and UI
   internationalization need further refinement; copy-to-clipboard and history
   navigation are planned. See [`TODO.md`](TODO.md).
5. **Optional research data:** dictionary and stylometry data are local-only
   and may be absent. Their licence, attribution, installation, and removal
   paths need decisions before release. Parallel-passage metadata is instead a
   tracked, approved package resource.
6. **Schema evolution:** fresh imports use the declared schema, but there is no
   migration system for old local databases.
7. **TUI data contract:** imported books are stored with Spanish names (for
   example, `Juan`), while `OpenGNTState` currently initializes with `John`.
   Navigation/reference parsing handles either language, but this default-name
   mismatch should be resolved so the first loaded verse is reliable across a
   newly imported database.

## 14. Maintenance rules for future changes

- Treat `paths.py` as the only supported source of default mutable-data paths;
  do not reintroduce package-local databases, settings, dictionaries, or
  backups.
- Extend `models.py` and fresh-import tests together whenever importer columns
  change. Add a migration strategy before claiming compatibility with existing
  databases.
- Preserve the safe setup boundary: local files only, acknowledgement,
  explicit optional selection, per-resource confirmation, atomic database
  construction, and local provenance recording.
- Do not reintroduce a downloader, scraper, hidden acquisition path, or
  destructive edition switch for unreviewed content.
- Keep presentation concerns in the TUI/CLI and reusable reading/writing logic
  in services/repositories. Add synthetic fixtures rather than real text data.
- Before publishing any asset, complete the provenance register and inspect
  both staged and ignored files:

  ```powershell
  git status --short
  git status --ignored --short
  git ls-files startup
  ```

- Run `uv run pytest -q` after changes to import, command, service, or display
  behaviour. A clean clone must continue to function for help and tests without
  any real biblical data.
