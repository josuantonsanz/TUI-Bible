from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, UniqueConstraint, TIMESTAMP
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()

# --- Text Models ---

class Book(Base):
    __tablename__ = 'books'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    canonical_order = Column(Integer, nullable=False)
    abbreviation = Column(String)

    words = relationship("Word", back_populates="book")

class Word(Base):
    __tablename__ = 'words'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ognt_sort = Column(Integer, nullable=False)
    tantt_sort = Column(Integer)
    features_sort = Column(Integer)
    levinsohn_clause_id = Column(String)
    ot_quotation = Column(String)

    book_id = Column(Integer, ForeignKey('books.id'), nullable=False)
    chapter = Column(Integer, nullable=False)
    verse = Column(Integer, nullable=False)
    word_order = Column(Integer, nullable=False)

    greek_koine = Column(String)
    greek_unaccented = Column(String)
    greek_accented = Column(String, nullable=False)
    lexeme = Column(String, nullable=False)

    strongs = Column(String)
    rmac = Column(String)

    bdag_entry = Column(String)
    ednt_entry = Column(String)
    mounce_entry = Column(String)
    gk_number = Column(String)
    ln_number = Column(String)

    trans_sbl_cap = Column(String)
    trans_sbl = Column(String)
    modern_greek = Column(String)
    fonetica = Column(String)

    tbesg_gloss = Column(String)
    it_translation = Column(String)
    lt_translation = Column(String)
    st_translation = Column(String)

    spanish_base = Column(String)

    punct_before = Column(String)
    punct_after = Column(String)

    note = Column(String)

    book = relationship("Book", back_populates="words")
    variants = relationship("Variant", back_populates="word")

    __table_args__ = (UniqueConstraint('book_id', 'chapter', 'verse', 'word_order'),)

# --- Translation Models ---

class LemmaTranslation(Base):
    __tablename__ = 'lemma_translations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    lemma = Column(String, nullable=False, unique=True)
    spanish_translation = Column(String, nullable=False)
    notes = Column(String)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

class WordTranslation(Base):
    __tablename__ = 'word_translations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    word_id = Column(Integer, ForeignKey('words.id'), nullable=False, unique=True)
    spanish_translation = Column(String, nullable=False)
    notes = Column(String)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

class PhraseTranslation(Base):
    __tablename__ = 'phrase_translations'

    id = Column(Integer, primary_key=True, autoincrement=True)

    book_id = Column(Integer, ForeignKey('books.id'), nullable=False)
    chapter = Column(Integer, nullable=False)
    verse = Column(Integer, nullable=False)
    phrase_start = Column(Integer, nullable=False)
    phrase_end = Column(Integer, nullable=False)

    spanish_translation = Column(String)
    latin_translation = Column(String)

    notes = Column(String)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

class VerseTranslation(Base):
    __tablename__ = 'verse_translations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey('books.id'), nullable=False)
    chapter = Column(Integer, nullable=False)
    verse = Column(Integer, nullable=False)
    spanish_text = Column(String)
    latin_text = Column(String)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint('book_id', 'chapter', 'verse'),)

# --- Annotation Models ---

class Annotation(Base):
    __tablename__ = 'annotations'

    id = Column(Integer, primary_key=True, autoincrement=True)

    annotation_type = Column(String, nullable=False)  # 'word', 'phrase', 'passage'

    book_id = Column(Integer, ForeignKey('books.id'), nullable=False)
    chapter = Column(Integer, nullable=False)
    verse = Column(Integer, nullable=False)
    word_id = Column(Integer, ForeignKey('words.id'))
    phrase_start = Column(Integer)
    phrase_end = Column(Integer)
    passage_end_chapter = Column(Integer)
    passage_end_verse = Column(Integer)

    content = Column(String, nullable=False)
    annotation_category = Column(String)

    show_in_export = Column(Boolean, default=True)
    export_as = Column(String, default='footnote')  # 'footnote', 'sidenote', 'inline'

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

class LemmaAnnotation(Base):
    __tablename__ = 'lemma_annotations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    lemma = Column(String, nullable=False)
    content = Column(String, nullable=False)
    annotation_category = Column(String)

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

# --- Variant Models ---

class Variant(Base):
    __tablename__ = 'variants'

    id = Column(Integer, primary_key=True, autoincrement=True)
    word_id = Column(Integer, ForeignKey('words.id'), nullable=False)

    variant_text = Column(String, nullable=False)
    variant_lexeme = Column(String)
    variant_strongs = Column(String)
    variant_rmac = Column(String)
    variant_gloss = Column(String)

    source = Column(String)
    notes = Column(String)
    is_primary = Column(Boolean, default=False)

    word = relationship("Word", back_populates="variants")

# --- Project Models ---

class Project(Base):
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

class ProjectPassage(Base):
    __tablename__ = 'project_passages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)

    book_id = Column(Integer, ForeignKey('books.id'), nullable=False)
    chapter_start = Column(Integer, nullable=False)
    verse_start = Column(Integer, nullable=False)
    chapter_end = Column(Integer, nullable=False)
    verse_end = Column(Integer, nullable=False)

    sequence_order = Column(Integer)
