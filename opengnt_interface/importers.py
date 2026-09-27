"""
OpenGNT CSV Importers
"""

import csv
import logging
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.logging import RichHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)]
)
logger = logging.getLogger("opengnt.importer")
console = Console()

# OpenGNT records the relationship between a main word and NA28 in the Note
# slot of the variant field using full-width symbols:
#   '＊' -> the main word differs from NA28 (substantive variant)
#   '＝' -> the main word matches NA28 apart from an orthographic difference
# Both carry the NA28 reading in Mvar, so both are used when NA28 is primary.
NA28_NOTE_MARKERS = ("＊", "＝")


@dataclass
class ImportStats:
    """Statistics for import process"""
    books_created: int = 0
    words_imported: int = 0
    variants_created: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class OpenGNTImporter:
    """Imports OpenGNT CSV data into SQLite database"""

    # NT Book mapping (book number -> name)
    BOOK_NAMES = {
        40: ("Mateo", "Mt", 1),
        41: ("Marcos", "Mc", 2),
        42: ("Lucas", "Lc", 3),
        43: ("Juan", "Jn", 4),
        44: ("Hechos", "Hch", 5),
        45: ("Romanos", "Rom", 6),
        46: ("1 Corintios", "1Co", 7),
        47: ("2 Corintios", "2Co", 8),
        48: ("Gálatas", "Gal", 9),
        49: ("Efesios", "Ef", 10),
        50: ("Filipenses", "Flp", 11),
        51: ("Colosenses", "Col", 12),
        52: ("1 Tesalonicenses", "1Ts", 13),
        53: ("2 Tesalonicenses", "2Ts", 14),
        54: ("1 Timoteo", "1Tm", 15),
        55: ("2 Timoteo", "2Tm", 16),
        56: ("Tito", "Tit", 17),
        57: ("Filemón", "Flm", 18),
        58: ("Hebreos", "Heb", 19),
        59: ("Santiago", "St", 20),
        60: ("1 Pedro", "1Pe", 21),
        61: ("2 Pedro", "2Pe", 22),
        62: ("1 Juan", "1Jn", 23),
        63: ("2 Juan", "2Jn", 24),
        64: ("3 Juan", "3Jn", 25),
        65: ("Judas", "Jud", 26),
        66: ("Apocalipsis", "Ap", 27),
    }

    def __init__(self, db_path: Path, primary_variant: str = 'opengnt', include_na28: bool = False):
        if primary_variant not in {'opengnt', 'na28'}:
            raise ValueError("primary_variant must be 'opengnt' or 'na28'")
        if primary_variant == 'na28' and not include_na28:
            raise ValueError("NA28 selection requires include_na28=True")
        self.db_path = db_path
        self.primary_variant = primary_variant
        self.include_na28 = include_na28
        self.conn: Optional[sqlite3.Connection] = None
        self.stats = ImportStats()
        self.rmac_cache: Dict[str, str] = {}

    def _connect(self):
        """Create database connection"""
        logger.info(f"Connecting to database: {self.db_path}")
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")

    def _create_schema(self):
        """Create all database tables using SQLAlchemy models"""
        logger.info("Creating database schema...")

        with console.status("[bold blue]Creating tables..."):
            # Use SQLAlchemy to create schema from models
            from sqlalchemy import create_engine
            from .models import Base
            
            # Create engine for schema creation
            engine = create_engine(f"sqlite:///{self.db_path}")
            Base.metadata.create_all(engine)
            
            # Re-ensure indices that might be specific to performance tuning
            # (SQLAlchemy creates indexes defined in models, but we can add extra if needed)
            cursor = self.conn.cursor()
            
            # These indices are already in models, but safe to keep as IF NOT EXISTS for double check
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_words_reference ON words(book_id, chapter, verse, word_order)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_words_lexeme ON words(lexeme)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_words_strongs ON words(strongs)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_words_ognt_sort ON words(ognt_sort)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_variants_word ON variants(word_id)")

            self.conn.commit()
            logger.info("✓ Schema created successfully using SQLAlchemy models")

    def _populate_books(self):
        """Insert book records"""
        logger.info("Populating books table...")

        cursor = self.conn.cursor()
        for book_id, (name, abbrev, order) in self.BOOK_NAMES.items():
            cursor.execute(
                "INSERT OR REPLACE INTO books (id, name, canonical_order, abbreviation) VALUES (?, ?, ?, ?)",
                (book_id, name, order, abbrev)
            )
            self.stats.books_created += 1

        self.conn.commit()
        logger.info(f"✓ Created {self.stats.books_created} book records")

    def _load_rmac_mapping(self, morphology_csv: Path) -> Dict[str, str]:
        """Load RMAC codes from morphology CSV"""
        logger.info(f"Loading RMAC morphology from: {morphology_csv}")

        if not morphology_csv.exists():
            logger.error(f"Morphology file not found: {morphology_csv}")
            raise FileNotFoundError(f"Required file not found: {morphology_csv}")

        rmac_map = {}

        try:
            with open(morphology_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='\t')

                for row in reader:
                    ognt_sort = row.get('OGNTsort', '').strip()
                    rmac = row.get('RMAC', '').strip()

                    if ognt_sort and rmac:
                        rmac_map[ognt_sort] = rmac

            logger.info(f"✓ Loaded {len(rmac_map)} RMAC entries")
            return rmac_map

        except Exception as e:
            logger.error(f"Failed to load RMAC morphology: {e}")
            raise

    def _parse_bracketed_field(self, field: str) -> List[str]:
        """Parse pipe-delimited field inside 【】brackets"""
        # Remove brackets
        field = field.strip()
        if field.startswith('〔') and field.endswith('〕'):
            field = field[1:-1]

        # Split on pipe
        return [part.strip() for part in field.split('｜')]

    def _parse_word_row(self, row: Dict[str, str], row_num: int) -> Optional[Dict]:
        """Parse a single CSV row into word data"""
        try:
            # Core sorting fields
            ognt_sort = row.get('OGNTsort', '').strip()
            tantt_sort = row.get('TANTTsort', '').strip() or None
            features_sort = row.get('FEATURESsort1', '').strip() or None
            levinsohn_clause = row.get('LevinsohnClauseID', '').strip() or None
            ot_quotation = row.get('OTquotation', '').strip() or None

            # Parse reference 〔Book｜Chapter｜Verse〕
            ref_field = row.get('〔Book｜Chapter｜Verse〕', '')
            ref_parts = self._parse_bracketed_field(ref_field)
            if len(ref_parts) != 3:
                raise ValueError(f"Invalid reference field: {ref_field}")

            book_id = int(ref_parts[0])
            chapter = int(ref_parts[1])
            verse = int(ref_parts[2])

            # Parse Greek text 〔OGNTk｜OGNTu｜OGNTa｜lexeme｜rmac｜sn〕
            greek_field = row.get('〔OGNTk｜OGNTu｜OGNTa｜lexeme｜rmac｜sn〕', '')
            greek_parts = self._parse_bracketed_field(greek_field)
            if len(greek_parts) != 6:
                raise ValueError(f"Invalid Greek field: {greek_field}")

            greek_koine = greek_parts[0] or None
            greek_unaccented = greek_parts[1] or None
            greek_accented = greek_parts[2]
            lexeme = greek_parts[3]
            # Ignore greek_parts[4] (RMAC from main file)
            strongs = greek_parts[5] or None

            # Get RMAC from cache (loaded from morphology file)
            rmac = self.rmac_cache.get(ognt_sort)

            # Parse lexicon references
            lex_field = row.get('〔BDAGentry｜EDNTentry｜MounceEntry｜GoodrickKohlenbergerNumbers｜LN-LouwNidaNumbers〕', '')
            lex_parts = self._parse_bracketed_field(lex_field)
            if len(lex_parts) >= 5:
                bdag = lex_parts[0] or None
                ednt = lex_parts[1] or None
                mounce = lex_parts[2] or None
                gk_num = lex_parts[3] or None
                ln_num = lex_parts[4] or None
            else:
                bdag = ednt = mounce = gk_num = ln_num = None

            # Parse transliterations
            trans_field = row.get('〔transSBLcap｜transSBL｜modernGreek｜Fonética_Transliteración〕', '')
            trans_parts = self._parse_bracketed_field(trans_field)
            if len(trans_parts) >= 4:
                trans_sbl_cap = trans_parts[0] or None
                trans_sbl = trans_parts[1] or None
                modern_greek = trans_parts[2] or None
                fonetica = trans_parts[3] or None
            else:
                trans_sbl_cap = trans_sbl = modern_greek = fonetica = None

            # Parse translations
            trans_field = row.get('〔TBESG｜IT｜LT｜ST｜Español〕', '')
            trans_parts = self._parse_bracketed_field(trans_field)
            if len(trans_parts) >= 5:
                tbesg = trans_parts[0] or None
                it_trans = trans_parts[1] or None
                lt_trans = trans_parts[2] or None
                st_trans = trans_parts[3] or None
                spanish = trans_parts[4] or None
            else:
                tbesg = it_trans = lt_trans = st_trans = spanish = None

            # Parse punctuation
            punct_field = row.get('〔PMpWord｜PMfWord〕', '')
            punct_parts = self._parse_bracketed_field(punct_field)
            if len(punct_parts) >= 2:
                punct_before = (punct_parts[0] or "").replace('¬', '')
                if punct_before == '<pm></pm>': punct_before = ""
                punct_before = punct_before or None
                
                punct_after = (punct_parts[1] or "").replace('¬', '')
                if punct_after == '<pm></pm>': punct_after = ""
                punct_after = punct_after or None
            else:
                punct_before = punct_after = None

            # Parse variant info
            var_field = row.get('〔Note｜Mvar｜Mlexeme｜Mrmac｜Msn｜MTBESG〕', '')
            var_parts = self._parse_bracketed_field(var_field)

            note = var_parts[0] if len(var_parts) > 0 else None
            if note:
                note = note.strip() or None

            variant_data = None
            if len(var_parts) > 1 and var_parts[1]:  # Has Mvar
                variant_data = {
                    'mvar': var_parts[1] or None,
                    'mlexeme': var_parts[2] if len(var_parts) > 2 else None,
                    'mrmac': var_parts[3] if len(var_parts) > 3 else None,
                    'msn': var_parts[4] if len(var_parts) > 4 else None,
                    'mtbesg': var_parts[5] if len(var_parts) > 5 else None,
                }

            return {
                'ognt_sort': ognt_sort,
                'tantt_sort': tantt_sort,
                'features_sort': features_sort,
                'levinsohn_clause_id': levinsohn_clause,
                'ot_quotation': ot_quotation,
                'book_id': book_id,
                'chapter': chapter,
                'verse': verse,
                'greek_koine': greek_koine,
                'greek_unaccented': greek_unaccented,
                'greek_accented': greek_accented,
                'lexeme': lexeme,
                'strongs': strongs,
                'rmac': rmac,
                'bdag_entry': bdag,
                'ednt_entry': ednt,
                'mounce_entry': mounce,
                'gk_number': gk_num,
                'ln_number': ln_num,
                'trans_sbl_cap': trans_sbl_cap,
                'trans_sbl': trans_sbl,
                'modern_greek': modern_greek,
                'fonetica': fonetica,
                'tbesg_gloss': tbesg,
                'it_translation': it_trans,
                'lt_translation': lt_trans,
                'st_translation': st_trans,
                'spanish_base': spanish,
                'punct_before': punct_before,
                'punct_after': punct_after,
                'note': note,
                'variant_data': variant_data,
            }

        except Exception as e:
            logger.error(f"Error parsing row {row_num}: {e}")
            self.stats.errors.append(f"Row {row_num}: {str(e)}")
            return None

    def _calculate_word_order(self, words: List[Dict]) -> List[Dict]:
        """Calculate word_order within each verse"""
        current_ref = None
        word_order = 0

        for word in words:
            ref = (word['book_id'], word['chapter'], word['verse'])
            if ref != current_ref:
                current_ref = ref
                word_order = 1
            else:
                word_order += 1

            word['word_order'] = word_order

        return words

    def _import_words(self, csv_path: Path):
        """Import words from main CSV"""
        logger.info(f"Importing words from: {csv_path}")

        if not csv_path.exists():
            logger.error(f"CSV file not found: {csv_path}")
            raise FileNotFoundError(f"Required file not found: {csv_path}")

        # First pass: parse all rows
        words = []

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')

            with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=console
            ) as progress:
                task = progress.add_task("[cyan]Parsing CSV rows...", total=None)

                for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                    word_data = self._parse_word_row(row, row_num)
                    if word_data:
                        words.append(word_data)
                    progress.advance(task)

        logger.info(f"Parsed {len(words)} words successfully")

        # Calculate word order
        words = self._calculate_word_order(words)

        # Second pass: insert into database
        cursor = self.conn.cursor()

        with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
            task = progress.add_task("[green]Inserting words...", total=len(words))

            for word in words:
                # When NA28 is the primary text, replace the main word with the
                # NA28 reading carried in the variant field.  Only rows marked
                # with a NA28 note symbol have a counterpart to activate.
                original_note = word.get('note') or ''
                swapped_to_na28 = False
                if (
                    self.primary_variant == 'na28'
                    and word['variant_data']
                    and word['variant_data']['mvar']
                    and any(marker in original_note for marker in NA28_NOTE_MARKERS)
                ):
                    # Store original OpenGNT data
                    original_data = {
                        'greek_accented': word['greek_accented'],
                        'lexeme': word['lexeme'],
                        'strongs': word['strongs'],
                        'rmac': word['rmac'],
                        'tbesg_gloss': word['tbesg_gloss']
                    }

                    # Overwrite main word data with the NA28 variant data
                    vdata = word['variant_data']
                    word['greek_accented'] = vdata['mvar']
                    word['lexeme'] = vdata['mlexeme']
                    word['strongs'] = vdata['msn']
                    word['rmac'] = vdata['mrmac']
                    word['tbesg_gloss'] = vdata['mtbesg']

                    # The new variant data is the original OpenGNT data
                    word['variant_data'] = {
                        'mvar': original_data['greek_accented'],
                        'mlexeme': original_data['lexeme'],
                        'mrmac': original_data['rmac'],
                        'msn': original_data['strongs'],
                        'mtbesg': original_data['tbesg_gloss'],
                    }
                    word['note'] = f'NA28 ({original_note})'
                    swapped_to_na28 = True

                # Insert word
                cursor.execute("""
                               INSERT INTO words (ognt_sort, tantt_sort, features_sort, levinsohn_clause_id,
                                                  ot_quotation,
                                                  book_id, chapter, verse, word_order,
                                                  greek_koine, greek_unaccented, greek_accented, lexeme,
                                                  strongs, rmac,
                                                  bdag_entry, ednt_entry, mounce_entry, gk_number, ln_number,
                                                  trans_sbl_cap, trans_sbl, modern_greek, fonetica,
                                                  tbesg_gloss, it_translation, lt_translation, st_translation,
                                                  spanish_base,
                                                  punct_before, punct_after, note)
                               VALUES (?, ?, ?, ?, ?,
                                       ?, ?, ?, ?,
                                       ?, ?, ?, ?,
                                       ?, ?,
                                       ?, ?, ?, ?, ?,
                                       ?, ?, ?, ?,
                                       ?, ?, ?, ?, ?,
                                       ?, ?, ?)
                               """, (
                                   word['ognt_sort'], word['tantt_sort'], word['features_sort'],
                                   word['levinsohn_clause_id'], word['ot_quotation'],
                                   word['book_id'], word['chapter'], word['verse'], word['word_order'],
                                   word['greek_koine'], word['greek_unaccented'], word['greek_accented'],
                                   word['lexeme'],
                                   word['strongs'], word['rmac'],
                                   word['bdag_entry'], word['ednt_entry'], word['mounce_entry'],
                                   word['gk_number'], word['ln_number'],
                                   word['trans_sbl_cap'], word['trans_sbl'], word['modern_greek'], word['fonetica'],
                                   word['tbesg_gloss'], word['it_translation'], word['lt_translation'],
                                   word['st_translation'], word['spanish_base'],
                                   word['punct_before'], word['punct_after'], word['note']
                               ))

                word_id = cursor.lastrowid
                self.stats.words_imported += 1

                # Insert the alternative reading if requested
                if self.include_na28 and word['variant_data'] and word['variant_data']['mvar']:
                    vdata = word['variant_data']

                    if swapped_to_na28:
                        # The main word is now the NA28 reading, so the stored
                        # variant is the original OpenGNT reading.
                        source = 'OpenGNT'
                        notes = f'Variant from OpenGNT ({original_note})'
                    else:
                        # The main word stays OpenGNT; the stored variant is NA28.
                        source = 'NA28'
                        notes = original_note
                    is_primary = 0

                    cursor.execute("""
                                   INSERT INTO variants (word_id, variant_text, variant_lexeme, variant_rmac,
                                                         variant_strongs, variant_gloss, source, notes, is_primary)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                   """, (
                                       word_id, vdata['mvar'], vdata['mlexeme'], vdata['mrmac'],
                                       vdata['msn'], vdata['mtbesg'], source, notes, is_primary
                                   ))

                    self.stats.variants_created += 1

                progress.advance(task)

                # Commit every 1000 rows
                if self.stats.words_imported % 1000 == 0:
                    self.conn.commit()

        # Final commit
        self.conn.commit()
        logger.info(f"✓ Imported {self.stats.words_imported} words")
        if self.stats.variants_created > 0:
            logger.info(f"✓ Created {self.stats.variants_created} variant entries")

    def run_import(self, main_csv: Path, morphology_csv: Path) -> ImportStats:
        """Execute the complete import process"""
        try:
            console.print("\n[bold cyan]═══ OpenGNT Database Import ═══[/bold cyan]\n")

            # Delete existing database
            if self.db_path.exists():
                logger.warning(f"Removing existing database: {self.db_path}")
                self.db_path.unlink()

            # Connect and create schema
            self._connect()
            self._create_schema()

            # Populate books
            self._populate_books()

            # Load RMAC morphology
            self.rmac_cache = self._load_rmac_mapping(morphology_csv)

            # Import words
            self._import_words(main_csv)

            # Report stats
            console.print("\n[bold green]═══ Import Complete ═══[/bold green]\n")
            console.print(f"  Books created:     {self.stats.books_created}")
            console.print(f"  Words imported:    {self.stats.words_imported:,}")
            console.print(f"  Variants created:  {self.stats.variants_created}")
            console.print(f"  Database size:     {self.db_path.stat().st_size / 1024 / 1024:.2f} MB")

            if self.stats.errors:
                console.print(f"\n[yellow]⚠ Warnings: {len(self.stats.errors)} rows had parsing issues[/yellow]")
                for error in self.stats.errors[:10]:  # Show first 10
                    console.print(f"  - {error}")
                if len(self.stats.errors) > 10:
                    console.print(f"  ... and {len(self.stats.errors) - 10} more")

            console.print(f"\n[bold green]✓ Database ready:[/bold green] {self.db_path}\n")

            return self.stats

        except Exception as e:
            logger.error(f"[bold red]Import failed:[/bold red] {e}")
            if self.conn:
                self.conn.rollback()
            raise

        finally:
            if self.conn:
                self.conn.close()

def populate_lemma_translations(db_path: str, csv_path: str):
    """
    Populates the lemma_translations table with Spanish glosses from a CSV file.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create the lemma_translations table if it doesn't exist
    # Table should exist from schema creation
    # cursor.execute("CREATE TABLE IF NOT EXISTS lemma_translations ...")

    # Read the Spanish glosses from the CSV file
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            for row in reader:
                # Assuming the CSV format is: number, lemma, gloss
                if len(row) == 3:
                    _, lemma, gloss = row
                    # Insert the gloss into the lemma_translations table
                    cursor.execute(
                        "INSERT OR IGNORE INTO lemma_translations (lemma, spanish_translation) VALUES (?, ?)",
                        (lemma, gloss)
                    )
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to populate lemma translations: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    pass
