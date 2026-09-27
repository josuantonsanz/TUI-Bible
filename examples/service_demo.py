import sys
import os

# Ensure the parent directory is in the path to import opengnt_interface
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from opengnt_interface.repositories import TextRepository, TranslationRepository, AnnotationRepository, ProjectRepository
from opengnt_interface.services import TranslationService, AnnotationService, ProjectService
from opengnt_interface.paths import database_path

def main():
    """
    Demonstrates the usage of the OpenGNT Interface Services.
    """
    print("--- OpenGNT Service Demo ---")

    # 1. Database Setup
    # Connect to the SQLite database
    engine = create_engine(f"sqlite:///{database_path()}")
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 2. Initialize Repositories
        text_repo = TextRepository(session)
        trans_repo = TranslationRepository(session)
        anno_repo = AnnotationRepository(session)
        proj_repo = ProjectRepository(session)

        # 3. Initialize Services
        # Services encapsulate business logic and coordinate between repositories
        trans_service = TranslationService(trans_repo, text_repo)
        anno_service = AnnotationService(anno_repo, text_repo)
        proj_service = ProjectService(proj_repo, text_repo)

        # --- Section A: Fetching and Translating Text ---
        print("\n[A] Fetching Colossians 1:24...")
        colossians = text_repo.get_book_by_name("Colossians")
        if not colossians:
            print("Error: Colossians not found in DB.")
            return

        words = text_repo.get_words_by_verse(colossians.id, 1, 24)
        print(f"Fetched {len(words)} words.")

        # Display original and translation
        print("Original -> Spanish:")
        for word in words[:5]: # Show first 5 words
            trans = trans_service.get_word_translation(word.id)
            print(f"  {word.greek_accented} ({word.lexeme}) -> {trans}")

        # --- Section B: Customizing Translations ---
        # Modify the translation of the first word locally (Instance Override)
        first_word = words[0]
        print(f"\n[B] Overriding translation for: {first_word.greek_accented}")
        
        trans_service.set_word_translation(first_word.id, "Ahora en este momento", "Instance override test")
        
        # Verify result
        new_trans = trans_service.get_word_translation(first_word.id)
        print(f"  New Translation: {new_trans}")

        # Modify a lemma globally (Lemma Override)
        # Be careful: this affects ALL instances of this word
        lemma = first_word.lexeme
        print(f"  Overriding lemma '{lemma}' globally...")
        trans_service.set_lemma_translation(lemma, "AHORA (Global)", "Lemma override test")
        
        # Verify (this usually takes precedence over default, but instance takes precedence over lemma)
        # Since we set an instance override above, it should still say "Ahora en este momento"
        check_trans = trans_service.get_word_translation(first_word.id)
        print(f"  Word ID {first_word.id} (Instance + Lemma set): {check_trans}")


        # --- Section C: Annotations ---
        print("\n[C] Adding Annotation...")
        # Add a note to the first word
        anno_service.add_word_annotation(
            word_id=first_word.id,
            content="This is a key theological term here.",
            category="Theology"
        )
        print("  Annotation added.")

        # Retrieve annotations
        annos = anno_service.get_verse_annotations(colossians.id, 1, 24)
        print(f"  Found {len(annos)} annotations in this verse:")
        for a in annos:
            print(f"    - Type: {a.annotation_type}, Content: '{a.content}'")

        # --- Section D: Managing Projects ---
        print("\n[D] Project Management...")
        proj_name = "Colossians Study"
        
        # Check if exists, if not create
        project = proj_service.get_project(proj_name)
        if not project:
            print(f"  Creating project '{proj_name}'...")
            project = proj_service.create_project(proj_name, "Deep dive into Colossians")
        else:
            print(f"  Project '{proj_name}' already exists.")

        # Add a passage to the project
        print("  Adding Colossians 1:1-29 to project...")
        proj_service.add_passage(proj_name, "Colossians", 1, 1, 1, 29)
        
        # Verify
        passages = proj_repo.get_project_passages(project.id)
        print(f"  Project now has {len(passages)} passage(s).")

        session.commit() # Ensure everything is saved
        print("\n--- Demo Completed Successfully ---")

    except Exception as e:
        print(f"\nError: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    main()
