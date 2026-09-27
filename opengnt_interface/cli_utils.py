"""
Utility module for OpenGNT CLI data formatting and serialization
"""
import json
import csv
import io
from typing import Dict, Any, List
from opengnt_interface.services import InterlinearVerse, InterlinearWord

def to_json(data: Any, indent=2) -> str:
    """Serialize data to JSON. Handles custom dataclasses."""
    
    def default_serializer(obj):
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        elif hasattr(obj, 'isoformat'):  # For datetime objects if any
            return obj.isoformat()
        else:
            return str(obj)
            
    return json.dumps(data, default=default_serializer, indent=indent, ensure_ascii=False)

def to_csv(data: List[Dict[str, Any]]) -> str:
    """Serialize a list of flat dictionaries to CSV string."""
    if not data:
        return ""
        
    output = io.StringIO()
    # Extract headers from the first dictionary
    fieldnames = list(data[0].keys())
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in data:
        writer.writerow(row)
        
    return output.getvalue()


def format_verse_plain_text(verse_data: InterlinearVerse) -> str:
    """Format a verse as minimalist plain text (Greek word -> Translation)."""
    if not verse_data or not verse_data.words:
        return ""
        
    lines = [f"--- {verse_data.reference} ---"]
    
    # Optional: Include full Spanish verse if available
    if verse_data.spanish_verse_text:
         lines.append(f"Text: {verse_data.spanish_verse_text}")
         lines.append("-" * 20)
         
    for w in verse_data.words:
        # Reconstruct word with punctuation
        pb = (w.punct_before or "").replace("<pm>", "").replace("</pm>", "")
        pa = (w.punct_after or "").replace("<pm>", "").replace("</pm>", "")
        greek = f"{pb}{w.text}{pa}".strip()
        
        # Determine translation to show
        trans = w.translation if isinstance(w.translation, str) else str(w.translation)
        
        lines.append(f"{greek:<15} | {trans:<20} | {w.lemma} ({w.morph})")
        
    return "\n".join(lines)


def flatten_word_data(word: InterlinearWord, reference: str = "") -> Dict[str, Any]:
    """Flattens nested InterlinearWord data for CSV export."""
    flat = {
        "reference": reference,
        "word_id": getattr(word, 'word_id', ''),
        "text": getattr(word, 'text', ''),
        "lemma": getattr(word, 'lemma', ''),
        "morphology": getattr(word, 'morph', ''),
        "strongs": getattr(word, 'strongs', ''),
        "translation": getattr(word, 'translation', ''),
        "original_gloss": getattr(word, 'original_gloss', ''),
    }
    
    # Extract high-level stylometry if present
    styledata = getattr(word, 'stylometry_data', None)
    if styledata:
        if "gospels" in styledata:
             flat["stylo_gospel_intensity"] = styledata["gospels"].get("intensity", 0)
             flat["stylo_gospel_owner"] = styledata["gospels"].get("owner_id", "")
        if "pauline" in styledata:
             flat["stylo_pauline_intensity"] = styledata["pauline"].get("pauline_intensity", 0)
        if "johannine" in styledata:
             flat["stylo_johannine_intensity"] = styledata["johannine"].get("johannine_intensity", 0)
             
    return flat

def format_concordance_plain_text(concordance_data: dict) -> str:
    """Formats concordance dictionary to plain text."""
    lines = []
    lines.append(f"Concordance for Lemma: {concordance_data.get('lemma', '')}")
    lines.append(f"Total Occurrences: {concordance_data.get('total_count', 0)}")
    lines.append("=" * 40)
    
    by_inflection = concordance_data.get('by_inflection', {})
    for infl_key, infl_data in by_inflection.items():
        try:
             form, morph = eval(infl_key) if isinstance(infl_key, str) else infl_key
        except:
             form, morph = str(infl_key), ""
             
        lines.append(f"\nForm: {form} | Morph: {morph} ({infl_data.get('expanded_morph', '')})")
        
        for group in infl_data.get('translation_groups', []):
             lines.append(f"  Translation: '{group.get('translation', '')}'")
             lines.append(f"  References: {group.get('references_string', '')}")
             
    return "\n".join(lines)
