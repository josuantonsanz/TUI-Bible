"""
Importer for Spanish and Latin verse translations.
"""

import json
import sqlite3
from pathlib import Path
from typing import Optional, Dict
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

console = Console()


class BibleTranslationImporter:
    """Imports verse translations from JSON files into the database."""
    
    def __init__(self, db_path: Path = Path("opengnt.db")):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        
    def _connect(self):
        """Connect to database."""
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        self.conn = sqlite3.connect(self.db_path)
        
    def _close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            
    def import_spanish_verses(self, json_path: Path) -> int:
        """
        Import Spanish verse translations from JSON file.
        
        Args:
            json_path: Path to spanish_bible.json
            
        Returns:
            Number of verses imported
        """
        console.print(f"[bold cyan]Importing Spanish verses from {json_path}[/bold cyan]")
        
        if not json_path.exists():
            raise FileNotFoundError(f"JSON file not found: {json_path}")
        
        # Load JSON data
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self._connect()
        cursor = self.conn.cursor()
        
        verses_imported = 0
        verses_updated = 0
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                # Count total verses
                total_verses = sum(
                    len(verses)
                    for book in data.values()
                    for verses in book["chapters"].values()
                )
                
                task = progress.add_task("[cyan]Importing Spanish verses...", total=total_verses)
                
                for book_id_str, book_data in data.items():
                    book_id = int(book_id_str)
                    
                    for chapter_str, verses in book_data["chapters"].items():
                        chapter = int(chapter_str)
                        
                        for verse_str, verse_text in verses.items():
                            verse = int(verse_str)
                            
                            # Try to update existing record first
                            cursor.execute("""
                                UPDATE verse_translations 
                                SET spanish_text = ?, updated_at = CURRENT_TIMESTAMP
                                WHERE book_id = ? AND chapter = ? AND verse = ?
                            """, (verse_text, book_id, chapter, verse))
                            
                            if cursor.rowcount > 0:
                                verses_updated += 1
                            else:
                                # Insert new record
                                cursor.execute("""
                                    INSERT INTO verse_translations 
                                    (book_id, chapter, verse, spanish_text)
                                    VALUES (?, ?, ?, ?)
                                """, (book_id, chapter, verse, verse_text))
                                verses_imported += 1
                            
                            progress.advance(task)
                            
                            # Commit every 100 verses
                            if (verses_imported + verses_updated) % 100 == 0:
                                self.conn.commit()
            
            # Final commit
            self.conn.commit()
            
            console.print(f"[bold green]✓ Successfully imported Spanish verses[/bold green]")
            console.print(f"[dim]New records: {verses_imported}[/dim]")
            console.print(f"[dim]Updated records: {verses_updated}[/dim]")
            
            return verses_imported + verses_updated
            
        except Exception as e:
            console.print(f"[bold red]Error importing Spanish verses: {e}[/bold red]")
            self.conn.rollback()
            raise
        finally:
            self._close()
    
    def import_latin_verses(self, json_path: Path) -> int:
        """
        Import Latin verse translations from JSON file.
        
        Args:
            json_path: Path to latin_vulgate.json
            
        Returns:
            Number of verses imported
        """
        console.print(f"[bold cyan]Importing Latin verses from {json_path}[/bold cyan]")
        
        if not json_path.exists():
            raise FileNotFoundError(f"JSON file not found: {json_path}")
        
        # Load JSON data
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self._connect()
        cursor = self.conn.cursor()
        
        verses_imported = 0
        verses_updated = 0
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                # Count total verses
                total_verses = sum(
                    len(verses)
                    for book in data.values()
                    for verses in book["chapters"].values()
                )
                
                task = progress.add_task("[cyan]Importing Latin verses...", total=total_verses)
                
                for book_id_str, book_data in data.items():
                    book_id = int(book_id_str)
                    
                    for chapter_str, verses in book_data["chapters"].items():
                        chapter = int(chapter_str)
                        
                        for verse_str, verse_text in verses.items():
                            verse = int(verse_str)
                            
                            # Try to update existing record first
                            cursor.execute("""
                                UPDATE verse_translations 
                                SET latin_text = ?, updated_at = CURRENT_TIMESTAMP
                                WHERE book_id = ? AND chapter = ? AND verse = ?
                            """, (verse_text, book_id, chapter, verse))
                            
                            if cursor.rowcount > 0:
                                verses_updated += 1
                            else:
                                # Insert new record
                                cursor.execute("""
                                    INSERT INTO verse_translations 
                                    (book_id, chapter, verse, latin_text)
                                    VALUES (?, ?, ?, ?)
                                """, (book_id, chapter, verse, verse_text))
                                verses_imported += 1
                            
                            progress.advance(task)
                            
                            # Commit every 100 verses
                            if (verses_imported + verses_updated) % 100 == 0:
                                self.conn.commit()
            
            # Final commit
            self.conn.commit()
            
            console.print(f"[bold green]✓ Successfully imported Latin verses[/bold green]")
            console.print(f"[dim]New records: {verses_imported}[/dim]")
            console.print(f"[dim]Updated records: {verses_updated}[/dim]")
            
            return verses_imported + verses_updated
            
        except Exception as e:
            console.print(f"[bold red]Error importing Latin verses: {e}[/bold red]")
            self.conn.rollback()
            raise
        finally:
            self._close()
    
    def import_both(self, spanish_path: Optional[Path] = None, 
                   latin_path: Optional[Path] = None) -> Dict[str, int]:
        """
        Import both Spanish and Latin translations.
        
        Args:
            spanish_path: Path to spanish_bible.json (optional)
            latin_path: Path to latin_vulgate.json (optional)
            
        Returns:
            Dictionary with import statistics
        """
        stats = {}
        
        if spanish_path:
            stats['spanish'] = self.import_spanish_verses(spanish_path)
        
        if latin_path:
            stats['latin'] = self.import_latin_verses(latin_path)
        
        return stats


if __name__ == "__main__":
    # Example usage
    importer = BibleTranslationImporter()
    
    spanish_path = Path("data/spanish_bible.json")
    if spanish_path.exists():
        importer.import_spanish_verses(spanish_path)
    else:
        console.print(f"[yellow]Spanish Bible JSON not found at {spanish_path}[/yellow]")
