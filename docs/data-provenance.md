# Data provenance and redistribution register

> **Working register — not legal advice.** Re-check the upstream terms before
> redistributing a dataset or a database built from it. Items marked *under
> review* must be confirmed by the maintainer before any further distribution.

## Distribution policy

The public repository contains the application code, documentation, synthetic
tests, the approved parallel-passage reference metadata at
`opengnt_interface/data/parallels.json`, and the reviewed datasets bundled under
`startup/`. Databases, settings, backups, personal annotations, and secrets
live in the per-user application-data directory and are ignored by Git.

Bundling a file here is a deliberate distribution decision backed by the
licence recorded below. It is not a statement that every possible input is
redistributable: the *Biblia de Jerusalén*-derived Spanish text stays
local-only.

## Bundled assets

| Asset | Source | Licence | Attribution requirement | Status |
| --- | --- | --- | --- | --- |
| `startup/OpenGNT_version3_3.csv` | [OpenGNT Project](https://github.com/eliranwong/OpenGNT) by Eliran Wong, v3.3 (2018). Base text compiled from the Berean Greek Bible (primarily Nestle 1904, public domain); includes keyed features, RMAC, Goodrick–Kohlenberger, Louw–Nida, BDAG/EDNT/Mounce references, and variant annotations. | **CC BY-SA 4.0** | "Open Greek New Testament Project by Eliran Wong ... Based on a work at https://github.com/eliranwong/OpenGNT." Share derivatives under the same licence. | Bundled |
| `startup/OpenGNT_morphology_Spanish.csv` | OpenGNT Project, `OpenGNT_morphology_Spanish.csv.zip`. | **CC BY-SA 4.0** | Same as above. | Bundled |
| `startup/GK_lemma_SpanishGloss.csv` | Spanish derivative of OpenGNT `Glossary/GK_lemma_EnglishGloss.csv`, produced by machine translation. | **CC BY-SA 4.0** (derivative) | Same as above; keep share-alike. | Bundled |
| `startup/abbotsmith.json` | *A Manual Greek Lexicon of the New Testament*, G. Abbott-Smith (1922), retrieved via the [Logeion API](https://logeion.uchicago.edu/) (University of Chicago). | Public-domain text; digitisation/API terms under review. | Attribution to Abbott-Smith and Logeion. | Bundled — **digitisation terms under review** |
| `startup/latin_vulgate.json` | Latin Vulgate (Clementine) retrieved from [sacred-texts.com](https://sacred-texts.com/bib/vul/). | Public domain. | None required; keep source note. | Bundled |
| `opengnt_interface/data/parallels.json` | 367-entry parallel-passage reference metadata consumed by `ParallelPassageService`; contains titles and references, not biblical text. | Project-owned. | — | Bundled |

The OpenGNT data is **share-alike**: any redistributed copy of these CSVs, or of
any database derived from them, must remain under CC BY-SA 4.0 with the
attribution above. The MIT licence on the application code does not override
that.

## Restricted / not distributed

| Asset | Reason | Public repository handling |
| --- | --- | --- |
| `startup/spanish_bible.json` | *Biblia de Jerusalén*-derived Spanish text, copyrighted. | **Never commit.** Keep local-only; installed only via `--include-bj` plus a `Y/N` licence confirmation. |
| NA28 / NA28-preferred readings | Copyrighted critical edition. | Not installed by the supported setup; never bundle text, variants, or fixtures. |
| BibleWorks/AGNT material, personal PDFs, keys, notes | Personal or restricted research material. | Keep outside the repository. |
| User-data `opengnt.db`, `provenance.json`, settings, backups, annotations | Locally created runtime state. | Never publish; written outside the checkout. |
| `opengnt_interface/translations/en.json`, `es.json` | Project UI strings. | Covered by the project code licence. |

## Before adding or changing a bundled asset

1. Record the authoritative upstream URL, edition/version/date, retrieval date,
   checksum, and the exact licence or written permission.
2. Confirm that redistribution, modification, conversion, and database storage
   are each allowed.
3. Add the required attribution to `THIRD-PARTY-NOTICES.md` and any needed
   in-app notice.
4. Keep the file in `startup/` and document it in `startup/README.md`.
5. Add or reuse a synthetic, non-infringing fixture for tests; never make CI
   depend on the real asset.
6. Update this register before changing `.gitignore` or the setup defaults.
