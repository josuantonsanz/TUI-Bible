"""
Command-line Interface for OpenGNT Interface
"""

import sys

# Greek and other Unicode text is normal CLI output.  Windows may otherwise
# inherit a legacy console code page that cannot render the import diagnostics.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import json
import shutil
import tempfile
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

import typer
from rich.console import Console

# Adjust path to ensure imports work
sys.path.append(str(Path(__file__).parent.parent))

from opengnt_interface.importers import OpenGNTImporter
from opengnt_interface.repositories import TextRepository
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from opengnt_interface.cli_utils import to_json, to_csv, format_verse_plain_text, flatten_word_data
from opengnt_interface.services import InterlinearService, TranslationService, VariantService, ParallelPassageService
from opengnt_interface.repositories import TranslationRepository, VariantRepository
from opengnt_interface.bible_books import parse_reference
from opengnt_interface.paths import backups_directory, database_path, dictionary_path

app = typer.Typer(help="OpenGNT Interface CLI")
console = Console()


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _required_input(input_dir: Path, filename: str) -> Path:
    path = input_dir / filename
    if not path.is_file():
        raise typer.BadParameter(f"Required local input not found: {path}")
    return path


def _confirm_optional_resource(label: str, path: Path) -> None:
    """Require an interactive, per-resource acknowledgement for local add-ons."""
    prompt = (
        f"You selected {label} ({path}). Do you have all required rights to use, "
        "convert, and store this resource locally?"
    )
    if not typer.confirm(prompt, default=False):
        console.print(f"[yellow]Skipped setup: rights were not confirmed for {label}.[/yellow]")
        raise typer.Exit(code=2)


def _default_input_dir() -> Path:
    """Locate the bundled startup inputs relative to the checkout."""
    candidates = [
        Path(__file__).resolve().parent.parent / "startup",
        Path.cwd() / "startup",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return candidates[0]


@app.command()
def setup(
    input_dir: Path = typer.Option(None, help="Directory containing startup inputs (defaults to the bundled startup/ directory)"),
    output: Path = typer.Option(None, help="Database to create (defaults to the user-data directory)"),
    full_install: bool = typer.Option(False, "--full-install", "-f", help="Install every bundled resource in one step, without prompts"),
    include_lemma_glosses: bool = typer.Option(False, help="Install the bundled GK Spanish-gloss CSV"),
    include_latin: bool = typer.Option(False, help="Install the bundled Latin translation JSON"),
    include_bj: bool = typer.Option(False, help="Install a local Biblia de Jerusalen JSON (restricted; not bundled)"),
    include_dictionary: bool = typer.Option(False, help="Install the bundled Abbott-Smith dictionary JSON"),
    acknowledge_local_data_rights: bool = typer.Option(False, help="Confirm you are entitled to use resources outside the reviewed distribution"),
    overwrite: bool = typer.Option(False, help="Replace an existing output database"),
):
    """Build a local database from the bundled inputs.

    By default this installs the OpenGNT reading plus every bundled optional
    resource (lemma glosses, Abbott-Smith dictionary, Latin translation) in one
    step.  It never downloads anything and deliberately omits embedded NA28
    variants.  The copyrighted Biblia de Jerusalen text is not bundled and is
    installed only on request with --include-bj and a rights acknowledgement.
    A provenance manifest is written next to the database.
    """
    input_dir = (input_dir or _default_input_dir()).expanduser()

    if full_install:
        include_lemma_glosses = True
        include_latin = True
        include_dictionary = True

    if not (include_lemma_glosses or include_latin or include_dictionary or include_bj):
        # Plain `setup` is the one-command install of the reviewed, bundled set.
        include_lemma_glosses = True
        include_latin = True
        include_dictionary = True

    if include_bj and not acknowledge_local_data_rights:
        console.print("[red]--include-bj requires --acknowledge-local-data-rights.[/red]")
        raise typer.Exit(code=2)
    if not input_dir.is_dir():
        console.print(f"[red]Input directory not found: {input_dir}[/red]")
        raise typer.Exit(code=1)

    main_csv = _required_input(input_dir, "OpenGNT_version3_3.csv")
    morph_csv = _required_input(input_dir, "OpenGNT_morphology_Spanish.csv")
    output = (output or database_path()).expanduser()
    if output.exists() and not overwrite:
        console.print(f"[red]Output already exists: {output}. Use --overwrite only after backing it up.[/red]")
        raise typer.Exit(code=1)

    selected_inputs = {"main_csv": main_csv, "morphology_csv": morph_csv}
    optional_inputs = [
        (include_lemma_glosses, "lemma_glosses", "GK_lemma_SpanishGloss.csv"),
        (include_latin, "latin", "latin_vulgate.json"),
        (include_bj, "bj", "spanish_bible.json"),
        (include_dictionary, "abbotsmith_dictionary", "abbotsmith.json"),
    ]
    for enabled, label, filename in optional_inputs:
        if enabled:
            selected_inputs[label] = _required_input(input_dir, filename)

    if include_bj:
        _confirm_optional_resource("Biblia de Jerusalen", selected_inputs["bj"])

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix="opengnt-setup-") as temporary_dir:
        temporary_db = Path(temporary_dir) / output.name
        try:
            stats = OpenGNTImporter(temporary_db, primary_variant="opengnt").run_import(main_csv, morph_csv)
            if include_lemma_glosses:
                from opengnt_interface.importers import populate_lemma_translations
                populate_lemma_translations(str(temporary_db), str(selected_inputs["lemma_glosses"]))
            if include_latin or include_bj:
                from opengnt_interface.bible_translation_importer import BibleTranslationImporter
                BibleTranslationImporter(temporary_db).import_both(
                    selected_inputs.get("bj"), selected_inputs.get("latin")
                )
        except Exception as error:
            console.print(f"[bold red]Setup failed; the existing database was left unchanged:[/bold red] {error}")
            raise typer.Exit(code=1) from error

        if output.exists():
            output.unlink()
        shutil.move(str(temporary_db), output)

    if include_dictionary:
        installed_dictionary = dictionary_path()
        installed_dictionary.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(selected_inputs["abbotsmith_dictionary"], installed_dictionary)

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "database": str(output),
        "acknowledged_local_data_rights": acknowledge_local_data_rights,
        "primary_variant": "opengnt",
        "na28_variants_installed": False,
        "inputs": {label: {"path": str(path), "sha256": _sha256(path)} for label, path in selected_inputs.items()},
    }
    manifest_path = output.with_name("provenance.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    console.print(f"[bold green]Setup complete.[/bold green] Database: {output}")
    console.print(f"Provenance manifest: {manifest_path}")
    console.print(f"Words: {stats.words_imported}; NA28 variants installed: 0")

@app.command()
def import_data(
    csv_path: Path = typer.Option(..., help="Path to main OpenGNT CSV file"),
    morph_path: Path = typer.Option(..., help="Path to morphology CSV file (keyedFeatures)"),
    db_path: Path = typer.Option(database_path(), help="Output SQLite database path"),
    variant_mode: str = typer.Option("opengnt", help="Primary text variant; only 'opengnt' is supported")
):
    """
    Import OpenGNT data into the database.
    """
    if not csv_path.exists():
        console.print(f"[red]Error: CSV file not found: {csv_path}[/red]")
        raise typer.Exit(code=1)

    if not morph_path.exists():
        console.print(f"[red]Error: Morphology file not found: {morph_path}[/red]")
        raise typer.Exit(code=1)

    console.print(f"[bold cyan]Starting import...[/bold cyan]")
    console.print(f"  Main CSV: {csv_path}")
    console.print(f"  Morphology: {morph_path}")
    console.print(f"  Target DB: {db_path}")

    if variant_mode != "opengnt":
        console.print("[red]NA28 selection is not supported by this command. Use only an authorised local workflow after edition-aware storage is implemented.[/red]")
        raise typer.Exit(code=2)

    try:
        importer = OpenGNTImporter(db_path, primary_variant="opengnt")
        # Note: importers.py OpenGNTImporter.run_import takes (main_csv, morphology_csv)
        stats = importer.run_import(csv_path, morph_path)
        
        console.print(f"[bold green]Import finished successfully![/bold green]")
        console.print(f"  Words: {stats.words_imported}")
        console.print(f"  Variants: {stats.variants_created}")

    except Exception as e:
        console.print(f"[bold red]Import failed:[/bold red] {e}")
        raise typer.Exit(code=1)

def _get_services(db_path: Path):
    """Helper to initialize database connection and services."""
    if not db_path.exists():
        console.print(f"[red]Error: Database not found: {db_path}[/red]")
        raise typer.Exit(code=1)
        
    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Initialize repositories
    text_repo = TextRepository(session)
    trans_repo = TranslationRepository(session)
    variant_repo = VariantRepository(session)
    
    # Initialize services
    trans_service = TranslationService(trans_repo, text_repo)
    variant_service = VariantService(variant_repo, text_repo)
    
    # Optional parallel service
    base_dir = Path(__file__).parent
    parallels_path = base_dir / "data" / "parallels.json"
    parallel_service = ParallelPassageService(str(parallels_path))
    
    interlinear_service = InterlinearService(
        text_repo, trans_service, variant_service, parallel_service
    )
    
    return interlinear_service, text_repo, session

@app.command()
def read(
    reference: str = typer.Argument(..., help="Passage reference (e.g. 'John 1:1' or '1 John 2:3-5')"),
    db_path: Path = typer.Option(database_path(), help="Path to SQLite database"),
    format: str = typer.Option("text", help="Output format: 'text', 'json', or 'csv'"),
):
    """
    Read a verse or range of verses.
    """
    interlinear_service, text_repo, session = _get_services(db_path)
    
    try:
        book_id, chapter, verse = parse_reference(reference)
        if book_id is None or chapter is None or verse is None:
            console.print(f"[red]Error: Could not parse reference: {reference}[/red]")
            raise typer.Exit(code=1)
            
        # Simplified: Just grab the single verse for now, extendable to passage later
        verse_data = interlinear_service.get_verse_data(book_id, chapter, verse)
        
        if not verse_data:
            console.print(f"[yellow]No data found for {reference}[/yellow]")
            return

        if format == "json":
            console.print(to_json(verse_data))
        elif format == "csv":
            flat_words = [flatten_word_data(w, verse_data.reference) for w in verse_data.words]
            console.print(to_csv(flat_words))
        else:
            console.print(format_verse_plain_text(verse_data))
            
    finally:
        session.close()

@app.command()
def word(
    identifier: str = typer.Argument(..., help="Word ID (numeric) or Lemma (text)"),
    db_path: Path = typer.Option(database_path(), help="Path to SQLite database"),
    format: str = typer.Option("json", help="Output format: 'text' or 'json'"),
):
    """
    Get exhaustive metadata for a specific word instance or lemma.
    """
    interlinear_service, text_repo, session = _get_services(db_path)
    
    try:
        # Check if identifier is numeric (Word ID)
        if identifier.isdigit():
            word_id = int(identifier)
            w = text_repo.get_word(word_id)
            if not w:
                 console.print(f"[red]Word ID {word_id} not found.[/red]")
                 return
                 
            # Fetch full context using get_verse_data to reuse logic
            verse_data = interlinear_service.get_verse_data(w.book_id, w.chapter, w.verse)
            target_iw = None
            if verse_data:
                 for iw in verse_data.words:
                      if iw.word_id == word_id:
                           target_iw = iw
                           break
                           
            if not target_iw:
                console.print(f"[yellow]Could not assemble full word data for {word_id}[/yellow]")
                return
                
            if format == "json":
                console.print(to_json(target_iw))
            else:
                out = [f"Word ID: {target_iw.word_id}", f"Text: {target_iw.text}", f"Lemma: {target_iw.lemma}", f"Morph: {target_iw.morph}", f"Strong's: {target_iw.strongs}", f"Translation: {target_iw.translation}"]
                if target_iw.stylometry_data:
                     out.append("Stylometry data available (use JSON output to view full details).")
                console.print("\n".join(out))
                
        else:
            # Identifier is a Lemma
            # Just return concordance structured data as it's the most comprehensive lemma view
            data = interlinear_service.get_concordance_data(identifier)
            if not data or data.get('total_count', 0) == 0:
                 console.print(f"[yellow]No occurrences found for lemma '{identifier}'[/yellow]")
                 return
                 
            if format == "json":
                console.print(to_json(data))
            else:
                from opengnt_interface.cli_utils import format_concordance_plain_text
                console.print(format_concordance_plain_text(data))
                
    finally:
        session.close()


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query (Greek or Translation)"),
    db_path: Path = typer.Option(database_path(), help="Path to SQLite database"),
    format: str = typer.Option("text", help="Output format: 'text' or 'json'"),
):
    """
    Search across Greek text and translations.
    """
    interlinear_service, text_repo, session = _get_services(db_path)
    
    try:
        results = interlinear_service.search(query)
        
        if format == "json":
            console.print(to_json(results))
        else:
            console.print(f"Search Type: {results['type']}")
            console.print(f"Total Results: {len(results['results'])}")
            console.print("-" * 40)
            for r in results['results']:
                console.print(f"{r['ref_link']}: {r['snippet_before']}[bold yellow]{r['match']}[/bold yellow]{r['snippet_after']}")
                
    finally:
        session.close()

@app.command()
def dictionary(
    lemma: str = typer.Argument(..., help="Greek lemma to look up"),
    db_path: Path = typer.Option(database_path(), help="Path to SQLite database"),
    format: str = typer.Option("text", help="Output format: 'text' or 'json'"),
):
    """
    Look up a lemma in the Abbott-Smith dictionary.
    """
    try:
        dict_path = dictionary_path()
        
        if not dict_path.exists():
             console.print(f"[red]Dictionary file not found at {dict_path}[/red]")
             return
             
        with open(dict_path, 'r', encoding='utf-8') as f:
             entries = json.load(f)
             
        html_def = entries.get(lemma)
        if not html_def:
             console.print(f"[yellow]No dictionary entry found for '{lemma}'[/yellow]")
             return
             
        if format == "json":
             console.print(json.dumps({"lemma": lemma, "html_definition": html_def}, ensure_ascii=False))
        else:
             # Very basic text stripping for CLI view
             import re
             text_def = re.sub(r'<[^>]+>', '', html_def)
             console.print(f"[bold]{lemma}[/bold]\n{text_def}")
    except Exception as e:
        console.print(f"[bold red]Dictionary lookup failed:[/bold red] {e}")


@app.command()
def stylometry(
    target: str = typer.Argument(..., help="Word ID, Lemma, or Reference"),
    db_path: Path = typer.Option(database_path(), help="Path to SQLite database"),
    format: str = typer.Option("json", help="Output format: 'json' only for data analysis"),
):
    """
    Get raw stylistic numeric data for a word or reference.
    Outputs JSON by default as this is primarily for programmatic analysis.
    """
    interlinear_service, text_repo, session = _get_services(db_path)
    
    try:
        if target.isdigit():
             # Word ID
             w = text_repo.get_word(int(target))
             if not w: return
             data = interlinear_service.stylometry_data.get(w.lexeme)
             console.print(to_json({"target": target, "type": "word_id", "lexeme": w.lexeme, "data": data}))
             
        elif " " in target or ":" in target:
             # Reference
             book_id, chapter, verse = parse_reference(target)
             if book_id:
                  verse_data = interlinear_service.get_verse_data(book_id, chapter, verse)
                  if verse_data:
                       results = []
                       for w in verse_data.words:
                            if w.stylometry_data:
                                 results.append({
                                      "word_id": w.word_id,
                                      "text": w.text,
                                      "lemma": w.lemma,
                                      "data": w.stylometry_data
                                 })
                       console.print(to_json({"target": target, "type": "reference", "results": results}))
        else:
             # Assume Lemma
             data = interlinear_service.stylometry_data.get(target)
             console.print(to_json({"target": target, "type": "lemma", "data": data}))
             
    finally:
        session.close()

@app.command()
def export(
    reference: str = typer.Argument(..., help="Passage reference (e.g. 'Matthew 1-28')"),
    db_path: Path = typer.Option(database_path(), help="Path to SQLite database"),
    file: Path = typer.Option(..., help="Output file path (.json or .csv)"),
):
    """
    Export comprehensive verse and word metadata to a file.
    """
    interlinear_service, text_repo, session = _get_services(db_path)
    
    try:
        # Simple parser for potentially broad ranges (e.g. "Matthew 1-5" or just "Matthew")
        # For this implementation, we'll try to parse a single verse or book
        # A robust range parser would be needed for production, but we stick to the basic parser for now
        book_id, chapter, verse = parse_reference(reference)
        
        if book_id is None:
             console.print(f"[red]Could not parse reference for export: {reference}[/red]")
             return
             
        # If verse is provided, export just that verse. If not, this is a placeholder 
        # for a broader export logic which would iterate chapters/verses
        if chapter and verse:
             verse_data = interlinear_service.get_verse_data(book_id, chapter, verse)
             if not verse_data:
                  return
                  
             if file.suffix == '.json':
                  with open(file, 'w', encoding='utf-8') as f:
                       f.write(to_json(verse_data))
             elif file.suffix == '.csv':
                  flat_words = [flatten_word_data(w, verse_data.reference) for w in verse_data.words]
                  with open(file, 'w', encoding='utf-8', newline='') as f:
                       f.write(to_csv(flat_words))
             else:
                  console.print("[red]Unsupported file extension. Use .json or .csv[/red]")
             
             console.print(f"[green]Successfully exported {reference} to {file}[/green]")
        else:
             console.print("[yellow]Broad range exports (e.g., whole book) require passage iteration logic not yet fully implemented in CLI.[/yellow]")
             console.print("Try exporting a specific verse like 'Matthew 1:1'.")
             
    finally:
        session.close()


@app.command()
def verify(
    db_path: Path = typer.Option(database_path(), help="Path to SQLite database")
):
    """
    Run basic verification checks on the database.
    """
    if not db_path.exists():
        console.print(f"[red]Error: Database not found: {db_path}[/red]")
        raise typer.Exit(code=1)
        
    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        console.print(f"[bold cyan]Verifying database: {db_path}[/bold cyan]")
        
        # Check Books
        from opengnt_interface.models import Book, Word, Variant
        books_count = session.query(Book).count()
        console.print(f"  Books: {books_count} (Expected 27)")
        
        if books_count == 27:
            console.print("  [green]✓ Books count correct[/green]")
        else:
            console.print("  [red]✗ Books count mismatch![/red]")
            
        # Check Words
        words_count = session.query(Word).count()
        console.print(f"  Words: {words_count}")
        
        # Check Variants
        variants_count = session.query(Variant).count()
        console.print(f"  Variants: {variants_count}")
        
        # Simple query test
        repo = TextRepository(session)
        john = repo.get_book_by_name("Juan")
        if john:
            words_j1 = repo.get_words_by_verse(john.id, 1, 1)
            console.print(f"  Juan 1:1 has {len(words_j1)} words.")
        else:
            console.print("  [yellow]⚠ Book 'Juan' not found for testing[/yellow]")

        console.print("[bold green]Verification complete.[/bold green]")

    except Exception as e:
        console.print(f"[bold red]Verification failed:[/bold red] {e}")
    finally:
        session.close()

@app.command()
def import_verse_translations(
    spanish: Path = typer.Option(None, help="Path to Spanish Bible JSON file"),
    latin: Path = typer.Option(None, help="Path to Latin Vulgate JSON file"),
    db_path: Path = typer.Option(database_path(), help="Path to SQLite database")
):
    """
    Import Spanish and/or Latin verse translations from JSON files.
    """
    from opengnt_interface.bible_translation_importer import BibleTranslationImporter
    
    if not spanish and not latin:
        console.print("[red]Error: Please specify at least one translation file (--spanish or --latin)[/red]")
        raise typer.Exit(code=1)
    
    if not db_path.exists():
        console.print(f"[red]Error: Database not found: {db_path}[/red]")
        raise typer.Exit(code=1)
    
    try:
        importer = BibleTranslationImporter(db_path)
        stats = importer.import_both(spanish, latin)
        
        console.print("[bold green]Import complete![/bold green]")
        if 'spanish' in stats:
            console.print(f"  Spanish verses: {stats['spanish']}")
        if 'latin' in stats:
            console.print(f"  Latin verses: {stats['latin']}")
            
    except Exception as e:
        console.print(f"[bold red]Import failed: {e}[/bold red]")
        raise typer.Exit(code=1)

@app.command()
def backup(
    db_path: Path = typer.Option(database_path(), help="Path to database to backup"),
    output_dir: Path = typer.Option(backups_directory(), help="Directory to store backups"),
    compress: bool = typer.Option(False, help="Compress backup with gzip")
):
    """
    Create a timestamped backup of the database.
    """
    import gzip
    
    if not db_path.exists():
        console.print(f"[red]Error: Database not found: {db_path}[/red]")
        raise typer.Exit(code=1)
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{db_path.stem}_backup_{timestamp}{db_path.suffix}"
    backup_path = output_dir / backup_name
    
    try:
        console.print(f"[cyan]Creating backup of {db_path}...[/cyan]")
        
        if compress:
            # Compress with gzip
            backup_path = backup_path.with_suffix(backup_path.suffix + '.gz')
            with open(db_path, 'rb') as f_in:
                with gzip.open(backup_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        else:
            # Simple copy
            shutil.copy2(db_path, backup_path)
        
        # Get file sizes
        original_size = db_path.stat().st_size / 1024 / 1024  # MB
        backup_size = backup_path.stat().st_size / 1024 / 1024  # MB
        
        console.print(f"[bold green]✓ Backup created successfully![/bold green]")
        console.print(f"  Location: {backup_path}")
        console.print(f"  Original size: {original_size:.2f} MB")
        console.print(f"  Backup size: {backup_size:.2f} MB")
        
        if compress:
            compression_ratio = (1 - backup_size / original_size) * 100
            console.print(f"  Compression: {compression_ratio:.1f}%")
        
    except Exception as e:
        console.print(f"[bold red]Backup failed: {e}[/bold red]")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()

