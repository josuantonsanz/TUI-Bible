import sys
import os

# Ensure the parent directory is in the path to import opengnt_interface
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from opengnt_interface.repositories import TextRepository, VariantRepository
from opengnt_interface.services import VariantService
from opengnt_interface.paths import database_path

def main():
    print("--- OpenGNT Variant Service Demo ---")

    # 1. Database Setup
    engine = create_engine(f"sqlite:///{database_path()}")
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 2. Init
        text_repo = TextRepository(session)
        var_repo = VariantRepository(session)
        var_service = VariantService(var_repo, text_repo)

        # 3. Get a target word (e.g., from John 1:1)
        # Assuming John 1:1 exists. If not, we'll search something common.
        # "In the beginning was the word" -> "arche"
        
        # Let's just grab the first word in the DB to be safe for demo
        # Or look for a specific book if we want context.
        print("Finding a word to attach variant to...")
        # Get something from Matthew 1:1 if loaded, or just first available
        words = text_repo.get_verse(40, 1, 1) # Matt 1:1
        if not words:
            # Try grabbing any word
            word = session.query(text_repo.db.query(TextRepository).model).first() # wait, hacky.
            # Use repo method
            # We don't have a get_all_words or similar efficient one in repo interface shown,
            # but we can try book 40 (Matthew).
            pass
        
        # Robust fetch:
        # Books are 40-66.
        book = text_repo.get_book(40) # Matthew
        if not book:
             # Try grabbing the first book
             books = text_repo.get_books()
             if books:
                 book = books[0]
        
        target_word = None
        if book:
            words = text_repo.get_words_by_verse(book.id, 1, 1)
            if words:
                target_word = words[0]
        
        if not target_word:
            print("Error: No words found in DB to test with.")
            return

        print(f"Target Word: {target_word.greek_accented} (ID: {target_word.id})")

        # 4. Add a Manual Variant
        print("\n[Action] Adding 'Western' variant...")
        var_service.add_manual_variant(
            word_id=target_word.id,
            variant_text="TestVariantWord",
            source="Codex Bezae (Demo)",
            notes="This is a test variant added by the demo script."
        )
        print("Variant added.")

        # 5. Retrieve Variants
        print("\n[Action] Retrieving variants...")
        variants = var_service.get_variants_for_word(target_word.id)
        
        print(f"Found {len(variants)} variant(s):")
        for v in variants:
            print(f"  - Text: {v.variant_text}")
            print(f"    Source: {v.source}")
            print(f"    Notes: {v.notes}")
            print(f"    Primary: {v.is_primary}")

        # 6. Verify Content
        found = any(v.variant_text == "TestVariantWord" for v in variants)
        if found:
            print("\nSUCCESS: Variant successfully stored and retrieved.")
        else:
            print("\nFAILURE: Created variant not found.")

        session.rollback() # Cleanup so we don't pollute DB with test data? 
        # Actually, user might want to see it. But for demo usually we rollback or delete.
        # Let's commit to prove persistence, or rollback to keep clean.
        # Given "verify" nature, maybe rollback is better so repeat runs don't accumulate.
        print("\nRolling back changes to keep DB clean...")
        session.rollback()

    except Exception as e:
        print(f"\nError: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    main()
