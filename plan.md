# Publication and release plan

## Current candidate state

The repository candidate contains the application code, documentation, synthetic
tests, the approved parallel-passage reference metadata at
`opengnt_interface/data/parallels.json`, and the reviewed source datasets bundled
under `startup/`:

- `OpenGNT_version3_3.csv` and `OpenGNT_morphology_Spanish.csv` (OpenGNT
  Project, CC BY-SA 4.0);
- `GK_lemma_SpanishGloss.csv` (CC BY-SA 4.0 derivative of the OpenGNT glossary);
- `abbotsmith.json` (Abbott-Smith 1922 via Logeion; digitisation terms under
  review);
- `latin_vulgate.json` (public-domain Vulgate);
- `bibliaEsp.pk` (the *Biblia de Jerusalén*-derived Spanish source).

NA28 variants, AGNT/BibleWorks material, PDFs, credentials, backups, and
personal annotations are not distributed.

The supported one-command local bootstrap is:

```powershell
uv sync
uv run opengnt setup --full-install
uv run opengnt-tui
```

`setup` reads the bundled inputs, builds a temporary database before moving it
into place, writes a local provenance manifest with checksums, and defaults to
the OpenGNT reading with no NA28 variant rows. A plain `setup` installs the same
bundled set, including the Spanish translation derived on the fly from
`startup/bibliaEsp.pk`.

## Completed remediation

- [x] Add the reviewed datasets to Git with source and licence records
  (`THIRD-PARTY-NOTICES.md`, `docs/data-provenance.md`, `startup/README.md`).
- [x] Add a one-command install (`setup --full-install`) and console entry
  points (`opengnt`, `opengnt-tui`).
- [x] Bundle the Biblia de Jerusalén source pickle and derive the importer JSON
  from it during setup.
- [x] Add the MIT code licence and package metadata; drop unused dependencies.
- [x] Add a safe setup path with overwrite protection and a provenance manifest.
- [x] Resolve the CLI/TUI/settings/database-path split with one user-data
  resolver and `OPENGNT_DATA_DIR` override.
- [x] Repair the fresh-import schema mismatch for `fonetica`, `it_translation`,
  `lt_translation`, and `st_translation`.
- [x] Correct tab-delimited CSV handling and make the default import omit NA28
  variants.
- [x] Remove the unmaintained `scripts/` tree, the legacy prompt-toolkit UI,
  AGNT inspection tools, destructive NA28 migration code, scraper diagnostics,
  and dictionary download tools that were not part of the supported path.
- [x] Replace database-dependent tests with synthetic importer/CLI tests.
- [x] Validate a full local import from the bundled inputs: 138,013 words, 27
  books, zero NA28 variants, and a successful database verification.

## Remaining blockers and follow-ups

1. **Abbott-Smith digitisation terms.** Confirm Logeion's terms of use before
   relying on `abbotsmith.json` as a redistributed asset; otherwise move it back
   to a user-supplied input.
2. **NA28 and other editions.** Design edition-aware storage before offering an
   NA28 choice. The current schema must not mutate the base text or conflate
   edition-specific readings with OpenGNT data.
3. **Translation resources.** Replace fixed `spanish_text` and `latin_text`
   fields with resource/edition metadata and attribution records.
4. **Stylometry.** The optional stylometry data is not part of the bundled set;
   confirm how it is generated and loaded before documenting it as a feature.
5. **Release testing.** Test a clean clone on supported platforms. Cover setup
   failure modes, overwrite handling, provenance manifest output, and the TUI's
   no-database guidance.
6. **Repository size.** The bundled OpenGNT CSV is ~44 MB. Confirm plain Git is
   acceptable (it is a fixed historical release) or move it to Git LFS / a
   documented download step.

## Pre-release checklist

Before creating the first public commit or release:

- [x] Run `uv run pytest -q` in a clean checkout.
- [ ] Inspect `git status --short` and `git status --ignored --short`.
- [ ] Confirm that `git ls-files startup` lists only the bundled datasets and
  `startup/README.md`, never `spanish_bible.json`.
- [ ] Confirm that no database, PDF, key, backup, or generated output is staged.
- [ ] Review every staged filename and size, including the bundled CSVs.
- [ ] Confirm the maintainer accepts the bundled-data licences and the
  Abbott-Smith follow-up.
- [ ] Add `[project.urls]` metadata once the public repository exists.
