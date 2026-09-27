from sqlalchemy.orm import Session
from .models import Book, Word, LemmaTranslation, WordTranslation, PhraseTranslation, VerseTranslation, Annotation, LemmaAnnotation, Variant, Project, ProjectPassage

class TextRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_book(self, book_id: int) -> Book:
        return self.db.query(Book).filter(Book.id == book_id).first()

    def get_books(self) -> list[Book]:
        return self.db.query(Book).order_by(Book.canonical_order).all()

    def get_book_by_name(self, name: str) -> Book | None:
        return self.db.query(Book).filter(Book.name == name).first()
        
    def get_book_word_count(self, book_id: int) -> int:
        from sqlalchemy import func
        return self.db.query(func.count(Word.id)).filter(Word.book_id == book_id).scalar()

    def get_word(self, word_id: int) -> Word:
        return self.db.query(Word).filter(Word.id == word_id).first()

    def get_words_by_verse(self, book_id: int, chapter: int, verse: int) -> list[Word]:
        return self.db.query(Word).filter(
            Word.book_id == book_id,
            Word.chapter == chapter,
            Word.verse == verse
        ).order_by(Word.word_order).all()

    def get_verse(self, book_id: int, chapter: int, verse: int) -> list[Word]:
        return self.get_words_by_verse(book_id, chapter, verse)

    def get_passage(self, book_id: int, chapter_start: int, verse_start: int, chapter_end: int, verse_end: int) -> list[Word]:
        return self.db.query(Word).filter(
            Word.book_id == book_id,
            Word.chapter >= chapter_start,
            Word.verse >= verse_start,
            Word.chapter <= chapter_end,
            Word.verse <= verse_end
        ).order_by(Word.chapter, Word.verse, Word.word_order).all()
    
    def get_words_by_lemma(self, lemma: str) -> list[Word]:
        return self.db.query(Word).filter(Word.lexeme == lemma).order_by(Word.book_id, Word.chapter, Word.verse, Word.word_order).all()
        
    def update_word(self, word_id: int, greek_accented: str, greek_unaccented: str, lexeme: str, rmac: str, strongs: str) -> bool:
        """Update a word's greek text and properties."""
        word = self.get_word(word_id)
        if word:
            word.greek_accented = greek_accented
            if greek_unaccented:
                word.greek_unaccented = greek_unaccented
            word.lexeme = lexeme
            word.rmac = rmac
            word.strongs = strongs
            self.db.commit()
            return True
        return False

    def move_word(self, word_id: int, direction: int) -> bool:
        """
        Move a word to the left (-1) or right (+1) within its verse.
        Swaps word_order with the neighbor.
        """
        word = self.get_word(word_id)
        if not word:
            return False

        current_order = word.word_order
        target_order = current_order + direction

        # Check neighbor existence
        neighbor = self.db.query(Word).filter(
            Word.book_id == word.book_id,
            Word.chapter == word.chapter,
            Word.verse == word.verse,
            Word.word_order == target_order
        ).first()

        if not neighbor:
            return False

        try:
            # Swap orders using a temporary value to avoid unique constraint violation.
            # Use -word.id to ensure it's absolutely unique even if multiple words are "lost".
            original_order = word.word_order
            word.word_order = -word.id
            self.db.flush()

            neighbor.word_order = original_order
            self.db.flush()
            
            word.word_order = target_order
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False

    def delete_word(self, word_id: int) -> bool:
        """Delete a word and re-sequence subsequent words in the verse."""
        word = self.get_word(word_id)
        if not word:
            return False

        book_id, chapter, verse, order = word.book_id, word.chapter, word.verse, word.word_order

        # Delete the word
        self.db.delete(word)
        self.db.flush()

        # Shift subsequent words (ascending order to avoid collisions)
        subsequent_words = self.db.query(Word).filter(
            Word.book_id == book_id,
            Word.chapter == chapter,
            Word.verse == verse,
            Word.word_order > order
        ).order_by(Word.word_order.asc()).all()

        for w in subsequent_words:
            w.word_order -= 1
            self.db.flush()
        
        self.db.commit()
        return True

    def insert_word(self, book_id: int, chapter: int, verse: int, order: int, data: dict) -> Word | None:
        """Shift words and insert a new word at the specified order."""
        # Shift existing words forward (descending to avoid constraint violation)
        existing_subsequent = self.db.query(Word).filter(
            Word.book_id == book_id,
            Word.chapter == chapter,
            Word.verse == verse,
            Word.word_order >= order
        ).order_by(Word.word_order.desc()).all()

        for w in existing_subsequent:
            w.word_order += 1
            self.db.flush()

        # Create new word. We'll use a high ognt_sort or copy from neighbor if possible.
        # For simplicity, we'll try to find the previous word's ognt_sort + 1
        prev_word = self.db.query(Word).filter(
            Word.book_id == book_id,
            Word.chapter == chapter,
            Word.verse == verse,
            Word.word_order == order - 1
        ).first()
        
        ognt_sort = (prev_word.ognt_sort + 1) if prev_word else 100 # Fallback

        new_word = Word(
            book_id=book_id,
            chapter=chapter,
            verse=verse,
            word_order=order,
            ognt_sort=ognt_sort,
            greek_accented=data.get('greek_accented', ''),
            greek_unaccented=data.get('greek_unaccented', ''),
            lexeme=data.get('lexeme', ''),
            rmac=data.get('rmac', ''),
            strongs=data.get('strongs', ''),
            punct_before='',
            punct_after='',
            spanish_base=''
        )
        
        self.db.add(new_word)
        self.db.commit()
        return new_word

    def update_punctuation(self, word_id: int, punct_before: str, punct_after: str) -> bool:
        word = self.get_word(word_id)
        if word:
            word.punct_before = punct_before
            word.punct_after = punct_after
            self.db.commit()
            return True
        return False
    
    def get_verse_translation(self, book_id: int, chapter: int, verse: int):
        vt = self.db.query(VerseTranslation).filter_by(
            book_id=book_id, chapter=chapter, verse=verse
        ).first()
        if vt:
            return vt.spanish_text, vt.latin_text
        return None, None

    def search_greek(self, query: str, limit: int = 500) -> list[Word]:
        """Search for Greek words by unaccented form or lexeme."""
        # Clean query
        query = query.strip()
        if not query:
            return []
            
        return self.db.query(Word).filter(
            (Word.greek_unaccented.contains(query)) | 
            (Word.lexeme.contains(query))
        ).limit(limit).all()

    def search_translation(self, query: str, limit: int = 500) -> list[VerseTranslation]:
        """Search in Spanish verse translations."""
        query = query.strip()
        if not query:
             return []
             
        return self.db.query(VerseTranslation).filter(
            VerseTranslation.spanish_text.contains(query)
        ).limit(limit).all()
        
    def get_context_words(self, word_id: int, window: int = 4) -> list[Word]:
        """Get 'window' words before and 'window' words after the target word in the same verse."""
        target = self.get_word(word_id)
        if not target:
            return []
            
        # Get all words in verse - simple approach, safe for verse size
        # Optimized approach would use word_order range query if we trust word_order completely
        # which we should, but fetching verse is robust.
        # Actually, let's trust word_order for efficiency if we can, but get_words_by_verse is cached/fast.
        
        words = self.get_words_by_verse(target.book_id, target.chapter, target.verse)
        
        # Sort just in case (though get_words_by_verse should store order)
        words.sort(key=lambda w: w.word_order)
        
        try:
            # Find index of target
            # Note: target might be a different instance if fetched separately, compare ID
            idx = next(i for i, w in enumerate(words) if w.id == word_id)
            
            start = max(0, idx - window)
            end = min(len(words), idx + window + 1)
            return words[start:end]
        except StopIteration:
            return []

class TranslationRepository:
    """Repository for managing translations"""
    def __init__(self, db: Session):
        self.db = db
    
    def get_lemma_translation(self, lemma: str) -> str | None:
        result = self.db.query(LemmaTranslation).filter(LemmaTranslation.lemma == lemma).first()
        return result.spanish_translation if result else None

    def get_word_translation(self, word_id: int) -> str | None:
        result = self.db.query(WordTranslation).filter(WordTranslation.word_id == word_id).first()
        return result.spanish_translation if result else None
    
    def get_phrase_translations(self, book_id: int, chapter: int, verse: int) -> list[PhraseTranslation]:
        return self.db.query(PhraseTranslation).filter(
            PhraseTranslation.book_id == book_id,
            PhraseTranslation.chapter == chapter,
            PhraseTranslation.verse == verse
        ).all()

    def add_word_translation(self, word_id: int, translation: str, notes: str = None) -> WordTranslation:
        """Add or update a word-specific translation override."""
        existing = self.db.query(WordTranslation).filter(WordTranslation.word_id == word_id).first()
        if existing:
            existing.spanish_translation = translation
            existing.notes = notes
            return existing
        else:
            new_trans = WordTranslation(word_id=word_id, spanish_translation=translation, notes=notes)
            self.db.add(new_trans)
            self.db.commit() # immediate commit for now, or could trust service to commit
            return new_trans

    def add_lemma_translation(self, lemma: str, translation: str, notes: str = None) -> LemmaTranslation:
        """Add or update a lemma-wide translation override."""
        existing = self.db.query(LemmaTranslation).filter(LemmaTranslation.lemma == lemma).first()
        if existing:
            existing.spanish_translation = translation
            existing.notes = notes
            return existing
        else:
            new_trans = LemmaTranslation(lemma=lemma, spanish_translation=translation, notes=notes)
            self.db.add(new_trans)
            self.db.commit()
            return new_trans
            
    def add_phrase_translation(self, book_id: int, chapter: int, verse: int, translation: str, phrase_start: int = 1, phrase_end: int = 999) -> PhraseTranslation:
        """Add or update a phrase translation (defaulting to whole verse)."""
        pt = self.db.query(PhraseTranslation).filter_by(
            book_id=book_id, chapter=chapter, verse=verse, 
            phrase_start=phrase_start, phrase_end=phrase_end
        ).first()

        if pt:
            pt.spanish_translation = translation
        else:
            pt = PhraseTranslation(
                book_id=book_id,
                chapter=chapter,
                verse=verse,
                phrase_start=phrase_start,
                phrase_end=phrase_end,
                spanish_translation=translation
            )
            self.db.add(pt)
        
        self.db.commit()
        return pt

    def search_phrase_translations(self, query: str, limit: int = 500) -> list[PhraseTranslation]:
        """Search in custom Spanish phrase translations."""
        query = query.strip()
        if not query:
            return []
        
        return self.db.query(PhraseTranslation).filter(
            PhraseTranslation.spanish_translation.contains(query)
        ).limit(limit).all()
            
class AnnotationRepository:
    """Repository for managing annotations"""
    def __init__(self, db: Session):
        self.db = db

    def get_annotations_by_verse(self, book_id: int, chapter: int, verse: int) -> list[Annotation]:
        return self.db.query(Annotation).filter(
            Annotation.book_id == book_id,
            Annotation.chapter == chapter,
            Annotation.verse == verse
        ).all()
        
    def add_annotation(self, 
                       annotation_type: str, 
                       book_id: int, 
                       chapter: int, 
                       verse: int, 
                       content: str,
                       word_id: int = None,
                       phrase_start: int = None,
                       phrase_end: int = None,
                       category: str = None) -> Annotation:
        """Create a new annotation."""
        annotation = Annotation(
            annotation_type=annotation_type,
            book_id=book_id,
            chapter=chapter,
            verse=verse,
            word_id=word_id,
            phrase_start=phrase_start,
            phrase_end=phrase_end,
            content=content,
            annotation_category=category
        )
        self.db.add(annotation)
        self.db.commit()
        return annotation

    def add_lemma_annotation(self, lemma: str, content: str, category: str = None) -> LemmaAnnotation:
        annotation = LemmaAnnotation(
            lemma=lemma,
            content=content,
            annotation_category=category
        )
        self.db.add(annotation)
        self.db.commit()
        return annotation

    def get_lemma_annotations(self, lemma: str) -> list[LemmaAnnotation]:
        return self.db.query(LemmaAnnotation).filter(LemmaAnnotation.lemma == lemma).all()
        
    def delete_word_annotations(self, word_id: int):
        """Delete all annotations for a specific word instance."""
        self.db.query(Annotation).filter(
            Annotation.word_id == word_id,
            Annotation.annotation_type == 'word'
        ).delete()
        self.db.commit()
        
    def delete_lemma_annotations(self, lemma: str):
        """Delete all annotations for a lemma."""
        self.db.query(LemmaAnnotation).filter(LemmaAnnotation.lemma == lemma).delete()
        self.db.commit()

    def delete_verse_annotations(self, book_id: int, chapter: int, verse: int):
        """Delete all verse-level annotations for a specific verse."""
        self.db.query(Annotation).filter(
            Annotation.book_id == book_id,
            Annotation.chapter == chapter,
            Annotation.verse == verse,
            Annotation.annotation_type == 'verse'
        ).delete()
        self.db.commit()


class ProjectRepository:
    """Repository for managing projects"""
    def __init__(self, db: Session):
        self.db = db
        
    def create_project(self, name: str, description: str = None) -> Project:
        project = Project(name=name, description=description)
        self.db.add(project)
        self.db.commit()
        return project
        
    def get_project_by_name(self, name: str) -> Project | None:
        return self.db.query(Project).filter(Project.name == name).first()
        
    def add_passage(self, 
                   project_id: int, 
                   book_id: int, 
                   chapter_start: int, 
                   verse_start: int, 
                   chapter_end: int, 
                   verse_end: int,
                   sequence: int = None) -> ProjectPassage:
        
        passage = ProjectPassage(
            project_id=project_id,
            book_id=book_id,
            chapter_start=chapter_start,
            verse_start=verse_start,
            chapter_end=chapter_end,
            verse_end=verse_end,
            sequence_order=sequence
        )
        self.db.add(passage)
        self.db.commit()
        return passage
        
    def get_project_passages(self, project_id: int) -> list[ProjectPassage]:
        return self.db.query(ProjectPassage).filter(
            ProjectPassage.project_id == project_id
        ).order_by(ProjectPassage.sequence_order).all()

class VariantRepository:
    """Repository for managing textual variants"""
    def __init__(self, db: Session):
        self.db = db

    def get_variants_by_word(self, word_id: int) -> list[Variant]:
        return self.db.query(Variant).filter(Variant.word_id == word_id).all()

    def add_variant(self, 
                    word_id: int, 
                    variant_text: str, 
                    source: str = None, 
                    notes: str = None,
                    is_primary: bool = False) -> Variant:
        variant = Variant(
            word_id=word_id,
            variant_text=variant_text,
            source=source,
            notes=notes,
            is_primary=is_primary
        )
        self.db.add(variant)
        self.db.commit()
        return variant

    def delete_variant(self, variant_id: int):
        variant = self.db.query(Variant).filter(Variant.id == variant_id).first()
        if variant:
            self.db.delete(variant)
            self.db.commit()

