"""
Business Logic Layer
"""
from dataclasses import dataclass
from typing import List, Optional
import json
import os
from .models import PhraseTranslation

@dataclass
class InterlinearWord:
    text: str
    lemma: str
    morph: str
    strongs: str
    translation: str
    original_gloss: str
    word_id: int
    variants: list
    punct_before: Optional[str] = None
    punct_after: Optional[str] = None
    stylometry_data: Optional[dict] = None

@dataclass
class InterlinearVerse:
    reference: str  # e.g. "Matt 1:1"
    words: List[InterlinearWord]
    phrase_translations: List[PhraseTranslation]
    spanish_verse_text: Optional[str] = None  # Complete Spanish verse translation
    latin_verse_text: Optional[str] = None  # Complete Latin verse translation
    parallel_pericopes: List[dict] = None  # List of matching pericopes from parallels.json


class InterlinearService:
    def __init__(self, text_repo, translation_service, variant_service, parallel_service=None):
        self.text_repo = text_repo
        self.translation_service = translation_service
        self.variant_service = variant_service
        self.parallel_service = parallel_service
        self.stylometry_data = {}
        self.load_stylometry_data()

    def load_stylometry_data(self):
        try:
            # Assuming the file is in opengnt_interface/data/stylometry.json
            import __main__
            if hasattr(__main__, '__file__'):
                base_dir = os.path.dirname(os.path.abspath(__main__.__file__))
                json_path = os.path.join(base_dir, 'data', 'stylometry.json')
            else:
                json_path = 'data/stylometry.json'
                
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    self.stylometry_data = json.load(f)
        except Exception as e:
            print(f"Error loading stylometry data: {e}")

    def get_verse_data(self, book_id: int, chapter: int, verse: int) -> Optional[InterlinearVerse]:
        """Aggregate all data for a single verse."""
        words = self.text_repo.get_words_by_verse(book_id, chapter, verse)
        if not words:
            return None

        # Get phrase translations for the verse
        phrase_translations = self.translation_service.translation_repo.get_phrase_translations(book_id, chapter, verse)
        
        # Get Spanish and Latin verse translations
        spanish_verse, latin_verse = self.text_repo.get_verse_translation(book_id, chapter, verse)

        interlinear_words = []
        for word in words:
            # Resolve translation
            translation = self.translation_service.get_word_translation(word.id)
            
            # Get variants
            variants = self.variant_service.get_variants_for_word(word.id)
            
            iw = InterlinearWord(
                text=word.greek_accented,
                lemma=word.lexeme,
                morph=word.rmac or "",
                strongs=word.strongs or "",
                translation=translation,
                original_gloss=word.tbesg_gloss or "",
                word_id=word.id,
                variants=variants,
                punct_before=word.punct_before,
                punct_after=word.punct_after,
                stylometry_data=self.stylometry_data.get(word.lexeme)
            )
            interlinear_words.append(iw)

        # Format reference string (simplified for now)
        book = self.text_repo.get_book(book_id)
        ref_str = f"{book.name} {chapter}:{verse}" if book else f"{chapter}:{verse}"

        # Get parallel passages
        parallels = []
        if self.parallel_service and book:
            parallels = self.parallel_service.get_parallels_for_verse(book.name, chapter, verse)

        return InterlinearVerse(
            reference=ref_str,
            words=interlinear_words,
            phrase_translations=phrase_translations,
            spanish_verse_text=spanish_verse,
            latin_verse_text=latin_verse,
            parallel_pericopes=parallels
        )

    def get_passage_data(self, book_id: int, chapter_start: int, verse_start: int, chapter_end: int, verse_end: int) -> List[InterlinearVerse]:
        """Aggregate data for a range of verses."""
        # This implementation iterates verse by verse. 
        # Optimized implementation could fetch all words and group by verse.
        verses_data = []
        
        # Naive iteration: simplistic assumption of chapter/verse progression is risky if not careful.
        # Better: ask repo for all words in range, then group in python.
        all_words = self.text_repo.get_passage(book_id, chapter_start, verse_start, chapter_end, verse_end)
        
        # Group words by (chapter, verse)
        from itertools import groupby
        def get_key(w): return (w.chapter, w.verse)
        
        for (chap, ver), group in groupby(all_words, key=get_key):
            words = list(group)
            
            # Re-implement verse logic using pre-fetched words to avoid N+1 queries if possible,
            # but for now reusing get_verse_data logic is cleaner structurally, though less performant.
            # Let's call get_verse_data to ensure consistency, acknowledging n+1 query potential.
            # Given local SQLite, it's likely acceptable for reasonable passage sizes.
            v_data = self.get_verse_data(book_id, chap, ver)
            if v_data:
                verses_data.append(v_data)
                
        return verses_data

    def get_concordance_data(self, lemma: str) -> dict:
        """
        Retrieves all occurrences of a lemma, grouped by surface form, morphology,
        and then by instance translation. Also returns a book-first grouping.
        """
        words = self.text_repo.get_words_by_lemma(lemma)
        lemma_trans = self.translation_service.get_lemma_translation_text(lemma)
        
        if not lemma_trans and words:
             lemma_trans = words[0].spanish_base
             
        import re
        def clean_trans(t):
            if not t: return ""
            return re.sub(r'[.,:;?¿!¡]', '', t).strip().lower()

        # Phase 1: Collect all occurrences with their metadata
        occurrences = []
        for word in words:
            translation = clean_trans(self.translation_service.get_word_translation(word.id))
            book = self.text_repo.get_book(word.book_id)
            book_label = book.abbreviation or book.name if book else "???"
            
            occ = {
                'id': word.id,
                'form': word.greek_accented,
                'morph': word.rmac or "",
                'translation': translation or "---",
                'book_id': word.book_id,
                'book_name': book.name if book else "???",
                'book_label': book_label,
                'chapter': word.chapter,
                'verse': word.verse,
                'ref_str': f"{book.name} {word.chapter}:{word.verse}" if book else f"{word.chapter}:{word.verse}",
                'short_ref': f"{book_label} {word.chapter}:{word.verse}"
            }
            occurrences.append(occ)

        # Phase 2: Group by Inflection (Form, Morph) -> Translation -> Refs
        # existing structure: groups[(form, morph)] = { 'translation_groups': [ {trans, refs_str, richer_refs: []} ] }
        by_inflection = {}
        from .morphology import expand_morphology
        
        for occ in occurrences:
            key = (occ['form'], occ['morph'])
            if key not in by_inflection:
                by_inflection[key] = {
                    'translation_groups': {},
                    'expanded_morph': expand_morphology(occ['morph'])
                }
            
            tg_map = by_inflection[key]['translation_groups']
            if occ['translation'] not in tg_map:
                tg_map[occ['translation']] = []
            
            tg_map[occ['translation']].append(occ)

        # Transform by_inflection to the expected list format for UI
        final_inflection = {}
        for key, group in by_inflection.items():
            t_groups = []
            for trans_text, occs in group['translation_groups'].items():
                # Build a display string like "Mt 1:1; 2:3"
                # Group occs by book for the display string
                book_map = {}
                for o in occs:
                    if o['book_label'] not in book_map:
                        book_map[o['book_label']] = []
                    book_map[o['book_label']].append(f"{o['chapter']}:{o['verse']}")
                
                parts = []
                for b_lbl, cvs in book_map.items():
                    parts.append(f"{b_lbl} {'; '.join(cvs)}")
                
                t_groups.append({
                    'translation': trans_text,
                    'references_string': ". ".join(parts),
                    'occurrences': occs # Pass raw objects for clickable logic
                })
            
            final_inflection[key] = {
                'translation_groups': t_groups,
                'expanded_morph': group['expanded_morph']
            }

        # Phase 3: Group by Book -> Inflection -> Translation -> Refs
        by_book = {}
        for occ in occurrences:
            b_name = occ['book_name']
            if b_name not in by_book:
                # We need the total word count for this book to calculate relative frequency in the UI
                # We can dynamically get it from text_repo
                total_book_words = self.text_repo.get_book_word_count(occ['book_id']) if hasattr(self.text_repo, 'get_book_word_count') else 0
                
                by_book[b_name] = {
                    'order': occ['book_id'], # For sorting
                    'total_words': total_book_words,
                    'inflections': {}
                }
            
            infl_map = by_book[b_name]['inflections']
            key = (occ['form'], occ['morph'])
            if key not in infl_map:
                infl_map[key] = {
                    'expanded_morph': expand_morphology(occ['morph']),
                    'translations': {}
                }
            
            trans_map = infl_map[key]['translations']
            if occ['translation'] not in trans_map:
                trans_map[occ['translation']] = []
            
            trans_map[occ['translation']].append(occ)

        return {
            'lemma': lemma,
            'lemma_translation': lemma_trans,
            'total_count': len(words),
            'by_inflection': final_inflection,
            'by_book': by_book
        }

    def search(self, query: str) -> dict:
        """
        Global search function.
        Heuristic: if query (normalized) contains Greek characters, search greek words.
        Otherwise search translations.
        
        Returns:
            {
                "type": "greek" | "translation",
                "results": [
                    {
                        "ref": "John 1:1",
                        "ref_link": "John 1:1",
                        "snippet_before": "...",
                        "match": "...",
                        "snippet_after": "...",
                        "book_order": 1
                        ...
                    }
                ]
            }
        """
        if not query:
            return {"type": "none", "results": []}

        # Heuristic for Language
        # Greek block is approx U+0370 to U+03FF and U+1F00 to U+1FFF (Extended)
        # Simple check: do we have any characters in that range?
        def is_greek(s):
            for char in s:
                code = ord(char)
                if (0x0370 <= code <= 0x03FF) or (0x1F00 <= code <= 0x1FFF):
                    return True
            return False

        results = []
        is_greek_query = is_greek(query)
        
        if is_greek_query:
            # Search Greek Words
            # We normalize input somewhat? Let's assume user types mostly unaccented
            # or we rely on repo's LIKE query which is case sensitive usually but SQLite LIKE is case-insensitive for ASCII, 
            # for Unicode it depends on extensions.
            # Best is to search both lexeme and unaccented.
            words = self.text_repo.search_greek(query)
            
            for w in words:
                # Build context
                context = self.text_repo.get_context_words(w.id, window=4)
                # Split context into before/after
                # context is list of sorted words including target
                
                before_str = ""
                after_str = ""
                
                # Careful not to duplicate the match if it appears multiple times in context?
                # Actually context list *contains* the match word.
                
                # Reconstruct text
                # Simple reconstruction: space joined.
                # Ideally use punctuation logic, but for snippets simple is fine.
                
                c_idx = -1
                for i, cw in enumerate(context):
                    if cw.id == w.id:
                        c_idx = i
                        break
                
                if c_idx >= 0:
                     # For Greek, we want to include punctuation if available
                     def get_full_text(w):
                         pb = (w.punct_before or "").replace("<pm>", "").replace("</pm>", "").replace("¶", "").strip()
                         pa = (w.punct_after or "").replace("<pm>", "").replace("</pm>", "").replace("¶", "").strip()
                         return f"{pb}{w.greek_accented}{pa}"

                     before_words = [get_full_text(x) for x in context[:c_idx]]
                     after_words = [get_full_text(x) for x in context[c_idx+1:]]
                     before_str = " ".join(before_words)
                     if before_str: before_str += " "
                     after_str = " ".join(after_words)
                     if after_str: after_str = " " + after_str
                
                book = self.text_repo.get_book(w.book_id)
                book_name = book.name if book else "?"
                book_order = book.canonical_order if book else 999
                
                results.append({
                    "ref": f"{book_name} {w.chapter}:{w.verse}",
                    "short_ref": f"{w.chapter}:{w.verse}",
                    "ref_link": f"{book_name} {w.chapter}:{w.verse}",
                    "snippet_before": before_str,
                    "match": w.greek_accented,
                    "snippet_after": after_str,
                    "book_order": book_order,
                    "book_name": book_name
                })
                
        else:
            # Search Translations
            # Search both PhraseTranslation (priority) and VerseTranslation
            pts = self.translation_service.translation_repo.search_phrase_translations(query)
            vts = self.text_repo.search_translation(query)
            
            # Group by verse reference to handle priority
            verse_matches = {} # (book_id, chapter, verse) -> {'type': 'phrase'|'verse', 'obj': pt|vt}
            
            for pt in pts:
                key = (pt.book_id, pt.chapter, pt.verse)
                verse_matches[key] = {'type': 'phrase', 'obj': pt}
                
            for vt in vts:
                key = (vt.book_id, vt.chapter, vt.verse)
                if key not in verse_matches:
                    verse_matches[key] = {'type': 'verse', 'obj': vt}
            
            for (bid, chap, ver), match_info in verse_matches.items():
                if match_info['type'] == 'phrase':
                    text = match_info['obj'].spanish_translation
                else:
                    text = match_info['obj'].spanish_text
                    
                if not text: continue
                
                idx = text.lower().find(query.lower())
                if idx == -1: continue 
                
                match_text = text[idx : idx+len(query)]
                
                char_window = 30
                start_idx = max(0, idx - char_window)
                end_idx = min(len(text), idx + len(query) + char_window)
                
                s_before = text[start_idx:idx]
                s_after = text[idx+len(query):end_idx]
                
                book = self.text_repo.get_book(bid)
                book_name = book.name if book else "?"
                book_order = book.canonical_order if book else 999
                
                results.append({
                    "ref": f"{book_name} {chap}:{ver}",
                    "short_ref": f"{chap}:{ver}",
                    "ref_link": f"{book_name} {chap}:{ver}",
                    "snippet_before": s_before,
                    "match": match_text,
                    "snippet_after": s_after,
                    "book_order": book_order,
                    "book_name": book_name
                })

        return {
            "type": "greek" if is_greek_query else "translation",
            "results": results
        }

class TranslationService:
    def __init__(self, translation_repo, text_repo):
        self.translation_repo = translation_repo
        self.text_repo = text_repo

    def set_word_translation(self, word_id: int, translation: str, notes: str = None):
        """Override translation for a specific word instance."""
        return self.translation_repo.add_word_translation(word_id, translation, notes)

    def set_lemma_translation(self, lemma: str, translation: str, notes: str = None):
        """Override translation for a lemma globally."""
        return self.translation_repo.add_lemma_translation(lemma, translation, notes)

    def set_phrase_translation(self, book_id: int, chapter: int, verse: int, translation: str):
        """Set translation for the entire verse."""
        # For whole-verse translation, we default start/end to cover typical verse length
        return self.translation_repo.add_phrase_translation(book_id, chapter, verse, translation)
    
    def get_lemma_translation_text(self, lemma: str) -> str:
        """Get the translation for a lemma directly."""
        return self.translation_repo.get_lemma_translation(lemma) or ""

    def get_word_translation(self, word_id: int) -> str:
        """
        Get translation for a word using 3-tier lookup:
        1. Instance override (WordTranslation)
        2. Lemma override (LemmaTranslation)
        3. Default (Word.spanish_base)
        """
        # 1. Check instance override
        instance_trans = self.translation_repo.get_word_translation(word_id)
        if instance_trans:
            return instance_trans

        # Get word data to check lemma and base
        word = self.text_repo.get_word(word_id)
        if not word:
            return ""

        # 2. Check lemma override
        lemma_trans = self.translation_repo.get_lemma_translation(word.lexeme)
        if lemma_trans:
            return lemma_trans

        # 3. Fallback to default
        return word.spanish_base or "(No translation found)"

class AnnotationService:
    def __init__(self, annotation_repo, text_repo):
        self.annotation_repo = annotation_repo
        self.text_repo = text_repo

    def add_word_annotation(self, word_id: int, content: str, category: str = None):
        """Add an annotation to a specific word."""
        word = self.text_repo.get_word(word_id)
        if not word:
            raise ValueError(f"Word with ID {word_id} not found")
            
        return self.annotation_repo.add_annotation(
            annotation_type='word',
            book_id=word.book_id,
            chapter=word.chapter,
            verse=word.verse,
            word_id=word_id,
            content=content,
            category=category
        )

    def get_verse_annotations(self, book_id: int, chapter: int, verse: int):
        """Get all annotations for a verse."""
        return self.annotation_repo.get_annotations_by_verse(book_id, chapter, verse)

    def add_lemma_annotation(self, lemma: str, content: str, category: str = None):
        """Add an annotation to a lemma."""
        return self.annotation_repo.add_lemma_annotation(lemma, content, category)

    def get_annotations_for_word_id(self, word_id: int):
        """Get ALL annotations relevant to a word instance (instance + lemma)."""
        word = self.text_repo.get_word(word_id)
        if not word:
            return []
            
        # 1. Instance annotations (search by word_id)
        # Note: repositories.get_annotations_by_verse returns all for verse, we might want to filter?
        # For now, let's just get specific word annotations if we can, or filter the verse ones.
        # Ideally, repo should have get_annotations_by_word_id.
        # Let's add it to repo? Or filter here.
        verse_annos = self.annotation_repo.get_annotations_by_verse(word.book_id, word.chapter, word.verse)
        instance_annos = [a for a in verse_annos if a.word_id == word_id]
        
        # 2. Lemma annotations
        lemma_annos = self.annotation_repo.get_lemma_annotations(word.lexeme)
        
        return {
            'instance_annotations': instance_annos,
            'lemma_annotations': lemma_annos
        }

        
    def set_word_annotation(self, word_id: int, content: str):
        """Replace all annotations for a word with new content."""
        # For simplicity, we implement "set" as delete all + add new
        self.annotation_repo.delete_word_annotations(word_id)
        if content.strip():
            return self.add_word_annotation(word_id, content)
            
    def set_lemma_annotation(self, lemma: str, content: str):
        """Replace all annotations for a lemma with new content."""
        self.annotation_repo.delete_lemma_annotations(lemma)
        if content.strip():
            return self.add_lemma_annotation(lemma, content)

    def add_verse_annotation(self, book_id: int, chapter: int, verse: int, content: str, category: str = None):
        """Add an annotation to a specific verse."""
        return self.annotation_repo.add_annotation(
            annotation_type='verse',
            book_id=book_id,
            chapter=chapter,
            verse=verse,
            content=content,
            category=category
        )

    def set_verse_annotation(self, book_id: int, chapter: int, verse: int, content: str):
        """Replace all verse-level annotations with new content."""
        self.annotation_repo.delete_verse_annotations(book_id, chapter, verse)
        if content.strip():
            return self.add_verse_annotation(book_id, chapter, verse, content)


class DictionaryService:
    def __init__(self, dictionary_path: str):
        self.dictionary_path = dictionary_path
        self.entries = {}
        self.parser = None
        self._load_dictionary()

    def _load_dictionary(self):
        import json
        import os
        from .asparser import AbbottSmithParser
        
        self.parser = AbbottSmithParser()
        if os.path.exists(self.dictionary_path):
            try:
                with open(self.dictionary_path, "r", encoding="utf-8") as f:
                    self.entries = json.load(f)
            except Exception as e:
                print(f"Error loading dictionary: {e}")
        else:
            print(f"Dictionary file not found: {self.dictionary_path}")

    def get_definition(self, lemma: str):
        """Returns a formatted Rich Text object for the given lemma."""
        if not lemma:
            return None
        
        html_content = self.entries.get(lemma)
        if not html_content:
            # Try to find case-insensitive or partial match if needed?
            # For now, exact match as lemmas should be normalized.
            return None
            
        return self.parser.format_entry(html_content)


class ProjectService:
    def __init__(self, project_repo, text_repo):
        self.project_repo = project_repo
        self.text_repo = text_repo
        
    def create_project(self, name: str, description: str = None):
        if self.project_repo.get_project_by_name(name):
            raise ValueError(f"Project '{name}' already exists")
        return self.project_repo.create_project(name, description)
        
    def get_project(self, name: str):
        return self.project_repo.get_project_by_name(name)
        
    def add_passage(self, project_name: str, book_name: str, chapter_start: int, verse_start: int, chapter_end: int, verse_end: int):
        """Add a passage to a project."""
        project = self.get_project(project_name)
        if not project:
            raise ValueError(f"Project '{project_name}' not found")
            
        book = self.text_repo.get_book_by_name(book_name)
        if not book:
            raise ValueError(f"Book '{book_name}' not found")
            
        # Optional: Validate verses exist
        
        return self.project_repo.add_passage(
            project_id=project.id,
            book_id=book.id,
            chapter_start=chapter_start,
            verse_start=verse_start,
            chapter_end=chapter_end,
            verse_end=verse_end
        )

class ParallelPassageService:
    def __init__(self, parallels_path: str):
        self.parallels_path = parallels_path
        self.parallels = []
        self._load_parallels()

    def _load_parallels(self):
        import json
        import os
        if os.path.exists(self.parallels_path):
            try:
                with open(self.parallels_path, "r", encoding="utf-8") as f:
                    self.parallels = json.load(f)
            except Exception as e:
                print(f"Error loading parallels: {e}")

    def get_parallels_for_verse(self, book_name: str, chapter: int, verse: int) -> List[dict]:
        """
        Finds all pericopes that include the given verse.
        Returns a list of pericope objects with their references.
        """
        matches = []
        for p in self.parallels:
            for book, ref in p["references"].items():
                if book.lower() in book_name.lower():
                    if self._is_verse_in_ref(chapter, verse, ref):
                        matches.append(p)
                        break
        return matches

    def _is_verse_in_ref(self, chapter: int, verse: int, ref: str) -> bool:
        """
        Checks if a chapter:verse is within a reference string like '3:13-17' or '3:13; 4:1-5'.
        """
        # Handle multiple ranges separated by semicolon
        parts = [p.strip() for p in ref.split(";")]
        for part in parts:
            if ":" not in part:
                # Might be a single chapter or a verse in a previously established chapter?
                # Usually in this dataset, it's C:V or C:V-V or C:V-C:V
                continue
            
            # Simplified parsing: assume C:V-V or C:V
            # Example: '3:13-17' -> chap 3, verse 13 to 17
            # Example: '3:13' -> chap 3, verse 13
            # Example: '4:1-5:12' -> chap 4 verse 1 to chap 5 verse 12
            
            try:
                # Use regex to extract ranges
                # Possible formats:
                # 3:13
                # 3:13-17
                # 3:13-4:5
                match = re.match(r"(\d+):(\d+)(?:-(\d+)(?::(\d+))?)?", part)
                if not match:
                    continue
                
                start_chap = int(match.group(1))
                start_verse = int(match.group(2))
                end_chap = int(match.group(3) or start_chap) if match.group(4) else start_chap
                end_verse = int(match.group(4) or match.group(3) or start_verse)
                
                # If there's no match.group(4) but match.group(3) exists, it's C:V-V
                if match.group(3) and not match.group(4):
                    end_chap = start_chap
                    end_verse = int(match.group(3))

                if start_chap == end_chap:
                    if chapter == start_chap and start_verse <= verse <= end_verse:
                        return True
                else:
                    # Multi-chapter range
                    if start_chap < chapter < end_chap:
                        return True
                    if chapter == start_chap and verse >= start_verse:
                        return True
                    if chapter == end_chap and verse <= end_verse:
                        return True
            except:
                continue
                
        return False

class VariantService:
    def __init__(self, variant_repo, text_repo):
        self.variant_repo = variant_repo
        self.text_repo = text_repo

    def get_variants_for_word(self, word_id: int):
        return self.variant_repo.get_variants_by_word(word_id)
        
    def add_manual_variant(self, word_id: int, variant_text: str, source: str = None, notes: str = None):
        """Add a manually tracked variant."""
        # Validate word exists
        if not self.text_repo.get_word(word_id):
            raise ValueError(f"Word with ID {word_id} not found")
            
        return self.variant_repo.add_variant(word_id, variant_text, source, notes)

import re

class ExportService:
    pass
