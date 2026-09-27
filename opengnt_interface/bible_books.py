from typing import Dict, List, Optional, Tuple
import re

# Book number to standard English name
EN_BOOK_NAMES = {
    40: "Matthew", 41: "Mark", 42: "Luke", 43: "John", 44: "Acts",
    45: "Romans", 46: "1 Corinthians", 47: "2 Corinthians", 48: "Galatians",
    49: "Ephesians", 50: "Philippians", 51: "Colossians", 52: "1 Thessalonians",
    53: "2 Thessalonians", 54: "1 Timothy", 55: "2 Timothy", 56: "Titus",
    57: "Philemon", 58: "Hebrews", 59: "James", 60: "1 Peter", 61: "2 Peter",
    62: "1 John", 63: "2 John", 64: "3 John", 65: "Jude", 66: "Revelation"
}

# Book number to standard English abbreviation
EN_BOOK_ABBR = {
    40: "Mt", 41: "Mk", 42: "Lk", 43: "Jn", 44: "Ac",
    45: "Ro", 46: "1Co", 47: "2Co", 48: "Ga",
    49: "Eph", 50: "Php", 51: "Col", 52: "1Th",
    53: "2Th", 54: "1Ti", 55: "2Ti", 56: "Tit",
    57: "Phm", 58: "Heb", 59: "Jas", 60: "1Pe", 61: "2Pe",
    62: "1Jn", 63: "2Jn", 64: "3Jn", 65: "Jud", 66: "Re"
}

# Book number to standard Spanish name (as used in the project)
ES_BOOK_NAMES = {
    40: "Mateo", 41: "Marcos", 42: "Lucas", 43: "Juan", 44: "Hechos",
    45: "Romanos", 46: "1 Corintios", 47: "2 Corintios", 48: "Gálatas",
    49: "Efesios", 50: "Filipenses", 51: "Colosenses", 52: "1 Tesalonicenses",
    53: "2 Tesalonicenses", 54: "1 Timoteo", 55: "2 Timoteo", 56: "Tito",
    57: "Filemón", 58: "Hebreos", 59: "Santiago", 60: "1 Pedro", 61: "2 Pedro",
    62: "1 Juan", 63: "2 Juan", 64: "3 Juan", 65: "Judas", 66: "Apocalipsis"
}

# Book number to standard Spanish abbreviation
ES_BOOK_ABBR = {
    40: "Mt", 41: "Mc", 42: "Lc", 43: "Jn", 44: "Hch",
    45: "Ro", 46: "1Co", 47: "2Co", 48: "Gá",
    49: "Ef", 50: "Flp", 51: "Col", 52: "1Ts",
    53: "2Ts", 54: "1Ti", 55: "2Ti", 56: "Tit",
    57: "Flm", 58: "Heb", 59: "Stg", 60: "1Pe", 61: "2Pe",
    62: "1Jn", 63: "2Jn", 64: "3Jn", 65: "Jud", 66: "Ap"
}

# Comprehensive mapping of names and abbreviations to book numbers
BOOK_MAPPING = {
    # English
    "matthew": 40, "matt": 40, "mt": 40,
    "mark": 41, "mk": 41, "mr": 41,
    "luke": 42, "lk": 42, "lu": 42,
    "john": 43, "jn": 43, "joh": 43,
    "acts": 44, "ac": 44,
    "romans": 45, "rom": 45, "ro": 45,
    "1 corinthians": 46, "1 cor": 46, "1 co": 46, "i cor": 46, "i co": 46,
    "2 corinthians": 47, "2 cor": 47, "2 co": 47, "ii cor": 47, "ii co": 47,
    "galatians": 48, "gal": 48, "ga": 48,
    "ephesians": 49, "eph": 49, "ep": 49,
    "philippians": 50, "phil": 50, "php": 50, "pp": 50,
    "colossians": 51, "col": 51,
    "1 thessalonians": 52, "1 thess": 52, "1 th": 52, "i thess": 52, "i th": 52,
    "2 thessalonians": 53, "2 thess": 53, "2 th": 53, "ii thess": 53, "ii th": 53,
    "1 timothy": 54, "1 tim": 54, "1 ti": 54, "i tim": 54, "i ti": 54,
    "2 timothy": 55, "2 tim": 55, "2 ti": 55, "ii tim": 55, "ii ti": 55,
    "titus": 56, "tit": 56, "ti": 56,
    "philemon": 57, "philem": 57, "phlm": 57, "pm": 57,
    "hebrews": 58, "heb": 58,
    "james": 59, "jas": 59, "jm": 59,
    "1 peter": 60, "1 pet": 60, "1 pe": 60, "1 p": 60, "i pet": 60, "i pe": 60, "i p": 60,
    "2 peter": 61, "2 pet": 61, "2 pe": 61, "2 p": 61, "ii pet": 61, "ii pe": 61, "ii p": 61,
    "1 john": 62, "1 jn": 62, "1 j": 62, "i jn": 62, "i j": 62,
    "2 john": 63, "2 jn": 63, "2 j": 63, "ii jn": 63, "ii j": 63,
    "3 john": 64, "3 jn": 64, "3 j": 64, "iii jn": 64, "iii j": 64,
    "jude": 65, "jud": 65,
    "revelation": 66, "rev": 66, "re": 66,

    # Spanish
    "mateo": 40, "mat": 40,
    "marcos": 41, "marc": 41, "mc": 41,
    "lucas": 42, "luc": 42, "lc": 42,
    "juan": 43, "jua": 43,
    "hechos": 44, "hec": 44, "hch": 44,
    "romanos": 45,
    "1 corintios": 46, "1 cor": 46, "1 co": 46, "i corintios": 46,
    "2 corintios": 47, "2 cor": 47, "2 co": 47, "ii corintios": 47,
    "gálatas": 48, "gal": 48, "gl": 48, "galatas": 48,
    "efesios": 49, "ef": 49,
    "filipenses": 50, "flp": 50, "fili": 50, "fil": 50,
    "colosenses": 51, "col": 51,
    "1 tesalonicenses": 52, "1 tes": 52, "1 ts": 52, "i tesalonicenses": 52,
    "2 tesalonicenses": 53, "2 tes": 53, "2 ts": 53, "ii tesalonicenses": 53,
    "1 timoteo": 54, "1 tim": 54, "1 ti": 54, "i timoteo": 54,
    "2 timoteo": 55, "2 tim": 55, "2 ti": 55, "ii timoteo": 55,
    "tito": 56, "tit": 56,
    "filemón": 57, "filemon": 57, "film": 57, "flm": 57,
    "hebreos": 58, "heb": 58,
    "santiago": 59, "sant": 59, "stg": 59,
    "1 pedro": 60, "1 ped": 60, "1 pe": 60, "1 p": 60, "i pedro": 60,
    "2 pedro": 61, "2 ped": 61, "2 pe": 61, "2 p": 61, "ii pedro": 61,
    "1 juan": 62, "1 jn": 62, "1 j": 62, "i juan": 62,
    "2 juan": 63, "2 jn": 63, "2 j": 63, "ii juan": 63,
    "3 juan": 64, "3 jn": 64, "3 j": 64, "iii juan": 64,
    "judas": 65, "jud": 65,
    "apocalipsis": 66, "apoc": 66, "apo": 66, "ap": 66,
}

def normalize_book_name(name: str) -> str:
    """Normalize book name for mapping lookup."""
    name = name.lower().strip()
    # Handle jointed numbers (e.g., 1Tes -> 1 tes)
    name = re.sub(r'^([123])([a-z])', r'\1 \2', name)
    # Replace Roman numerals (I, II, III) with numbers
    name = re.sub(r'^i\s+', '1 ', name)
    name = re.sub(r'^ii\s+', '2 ', name)
    name = re.sub(r'^iii\s+', '3 ', name)
    # Handle jointed Roman numerals (e.g., ITes -> 1 tes)
    name = re.sub(r'^i([a-z])', r'1 \1', name)
    name = re.sub(r'^ii([a-z])', r'2 \1', name)
    name = re.sub(r'^iii([a-z])', r'3 \1', name)
    
    # Remove extra spaces
    name = re.sub(r'\s+', ' ', name)
    return name

def find_book_id(name: str) -> Optional[int]:
    """Find book ID by name or abbreviation."""
    norm_name = normalize_book_name(name)
    return BOOK_MAPPING.get(norm_name)

def get_standard_name(book_id: int, lang: str = "es") -> str:
    """Get standard book name by ID."""
    if lang == "en":
        return EN_BOOK_NAMES.get(book_id, "")
    return ES_BOOK_NAMES.get(book_id, "")

def get_standard_abbr(book_id: int, lang: str = "es") -> str:
    """Get standard book abbreviation by ID."""
    if lang == "en":
        return EN_BOOK_ABBR.get(book_id, "")
    return ES_BOOK_ABBR.get(book_id, "")

def parse_reference(ref: str) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """
    Parse a reference string like 'John 3:16' or '1 Cor 1,1' or 'Mateo 1 1'.
    Returns (book_id, chapter, verse).
    """
    ref = ref.strip()
    if not ref:
        return None, None, None

    # Step 1: Identify where the book name ends and numeric parts start.
    # Looking for the last occurrence of space followed by digits or the last space
    # that separates name from chapter.
    # Examples:
    # "Matthew 3:16" -> "Matthew" and "3:16"
    # "1 Corinthians 1:1" -> "1 Corinthians" and "1:1"
    # "1 Cor 1,1" -> "1 Cor" and "1,1"
    
    # regex to find the chapter:verse part at the end
    # Supports separators: :, ,, space
    match = re.search(r'\s+(\d+[:,\s]+\d+)$', ref)
    if match:
        book_part = ref[:match.start()].strip()
        numeric_part = match.group(1).strip()
        
        # Split numeric part by :, , or space
        c_v = re.split(r'[:,\s]+', numeric_part)
        try:
            chapter = int(c_v[0])
            verse = int(c_v[1]) if len(c_v) > 1 else 1
            
            book_id = find_book_id(book_part)
            return book_id, chapter, verse
        except (ValueError, IndexError):
            return None, None, None
            
    # Fallback for "John 3" (no verse)
    match = re.search(r'\s+(\d+)$', ref)
    if match:
        book_part = ref[:match.start()].strip()
        try:
            chapter = int(match.group(1))
            book_id = find_book_id(book_part)
            return book_id, chapter, 1
        except ValueError:
            pass
    # Fallback for just "John" (no chapter or verse)
    book_id = find_book_id(ref)
    if book_id is not None:
        return book_id, None, None

    return None, None, None
