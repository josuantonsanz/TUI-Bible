import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from opengnt_interface.repositories import TextRepository, AnnotationRepository
from opengnt_interface.services import AnnotationService
from opengnt_interface.models import Word
from opengnt_interface.paths import database_path

def main():
    print("--- Lemma Annotation Demo ---")

    engine = create_engine(f"sqlite:///{database_path()}")
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        text_repo = TextRepository(session)
        anno_repo = AnnotationRepository(session)
        anno_service = AnnotationService(anno_repo, text_repo)

        # 1. Find a word
        print("Finding a word (e.g., 'Logos' in John 1:1)...")
        # Let's try to find "logos"
        # We need a word to attach instance annotation to, and its lemma for lemma annotation.
        # Find John 1:1 if possible, or just the first word.
        # Book id for John is usually 43.
        john = text_repo.get_book_by_name("John")
        if not john:
            print("John not found, picking first book...")
            book = text_repo.get_books()[0]
        else:
            book = john

        words = text_repo.get_verse(book.id, 1, 1)
        if not words:
            print("No words found.")
            return

        target_word = words[-1] # Usually 'Logos' (word) is at the end? Or let's just pick index 0.
        print(f"Target Word: {target_word.greek_accented} (Lexeme: {target_word.lexeme})")

        # 2. Add Instance Annotation
        print("\n[A] Adding Instance Annotation...")
        anno_service.add_word_annotation(target_word.id, "Local instance note.", "Grammar")

        # 3. Add Lemma Annotation
        lemma = target_word.lexeme
        print(f"\n[B] Adding Lemma Annotation for '{lemma}'...")
        anno_service.add_lemma_annotation(lemma, "Global definition/concept note.", "Lexical")

        # 4. Fetch All Annotations
        print("\n[C] Retrieving annotations for this word instance...")
        results = anno_service.get_annotations_for_word_id(target_word.id)
        
        print(f"  Instance Annotations: {len(results['instance_annotations'])}")
        for a in results['instance_annotations']:
            print(f"    - [{a.annotation_category}] {a.content}")
            
        print(f"  Lemma Annotations:    {len(results['lemma_annotations'])}")
        for a in results['lemma_annotations']:
            print(f"    - [{a.annotation_category}] {a.content} (Applies to all '{a.lemma}')")

    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    main()
