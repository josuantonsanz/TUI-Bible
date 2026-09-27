# Third-party notices

This project bundles third-party datasets under `startup/`. The application
source code is MIT-licensed (see `LICENSE`), but **each dataset keeps its own
licence and attribution requirements**. This file records what is bundled, its
source, and its terms.

If you redistribute this repository, a built wheel/sdist, or any database
derived from `startup/`, you must keep the attribution below and honour the
share-alike requirement of the OpenGNT data.

## Bundled datasets

### OpenGNT Project data — `startup/OpenGNT_version3_3.csv`

- **Source:** Open Greek New Testament Project (OGNT) by Eliran Wong.
- **Upstream:** https://github.com/eliranwong/OpenGNT
- **Licence:** Creative Commons Attribution-ShareAlike 4.0 International
  (CC BY-SA 4.0) — https://creativecommons.org/licenses/by-sa/4.0/
- **Attribution:** "Open Greek New Testament Project by Eliran Wong is licensed
  under a Creative Commons Attribution-ShareAlike 4.0 International License.
  Based on a work at https://github.com/eliranwong/OpenGNT."
- **Notes:** The OGNT base text is compiled from the Berean Greek Bible, which
  is primarily based on the Greek New Testament edited by Eberhard Nestle
  (1904, public domain). The CSV also contains keyed-feature columns (RMAC,
  Goodrick–Kohlenberger, Louw–Nida, BDAG/EDNT/Mounce references, and variant
  annotations). Redistribution of the file and of any database built from it is
  subject to CC BY-SA 4.0.

### OpenGNT Spanish morphology — `startup/OpenGNT_morphology_Spanish.csv`

- **Source:** OpenGNT Project (Eliran Wong), `OpenGNT_morphology_Spanish.csv.zip`.
- **Upstream:** https://github.com/eliranwong/OpenGNT
- **Licence:** CC BY-SA 4.0 (same attribution as above).

### Spanish lemma glosses — `startup/GK_lemma_SpanishGloss.csv`

- **Source:** derived from OpenGNT's `Glossary/GK_lemma_EnglishGloss.csv`
  (CC BY-SA 4.0) by machine translation to Spanish for this project.
- **Licence:** CC BY-SA 4.0, as a derivative of the OpenGNT glossary. Because it
  is share-alike, redistributed copies and derivatives must keep this licence
  and attribution.

### Abbott-Smith dictionary — `startup/abbotsmith.json`

- **Source:** *A Manual Greek Lexicon of the New Testament* by George
  Abbott-Smith (T. & T. Clark, 1922), retrieved through the Logeion API
  (University of Chicago): https://logeion.uchicago.edu/
- **Underlying text:** public domain (author died 1948; first published 1922).
- **Notes:** The digitised/structured form was retrieved from Logeion. Review
  Logeion's terms of use before redistributing this file or a database built
  from it. `docs/data-provenance.md` tracks this item as still under review.

### Latin Vulgate — `startup/latin_vulgate.json`

- **Source:** Latin Vulgate (Clementine edition) verse text, retrieved from
  https://sacred-texts.com/bib/vul/ (see the historical scraper in the project
  history).
- **Licence:** public domain.
- **Notes:** Verify the source page terms if you redistribute the file itself.

## Not bundled

The Biblia de Jerusalén-derived Spanish text (`startup/spanish_bible.json`) is
**not** distributed with this project: it is copyrighted and may not be
redistributed. It is ignored by Git. See `docs/restricted-content-setup.md`.

## Application dependencies

Runtime and development dependencies and their licences are recorded in
`uv.lock` and by the packages themselves (Beautiful Soup, Rich, SQLAlchemy,
Textual, Typer, pytest).
