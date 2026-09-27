from dataclasses import dataclass, asdict, fields
import json
import os

from opengnt_interface.paths import settings_path

SETTINGS_FILE = settings_path()

@dataclass
class InterlinearConfig:
    """Configuration for interlinear display visibility."""
    show_greek: bool = True
    show_transliteration: bool = True
    show_lexical_info: bool = True  # Lemma, Strongs, Morph
    show_gloss: bool = True
    show_translation: bool = True
    show_phrase_translation: bool = True
    
    # Specific granular controls
    show_strongs: bool = True
    show_morphology: bool = True
    show_lemma: bool = True
    show_verse_annotations: bool = True
    show_spanish_translation: bool = True
    show_latin_translation: bool = True
    show_dictionary_panel: bool = False
    show_stylometry: bool = False
    language: str = "en"

    def save(self):
        """Save settings to JSON file."""
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=4)

    @classmethod
    def load(cls) -> "InterlinearConfig":
        """Load settings from JSON file or return default."""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Filter keys to only those in the dataclass
                    valid_keys = {f.name for f in fields(cls)}
                    filtered_data = {k: v for k, v in data.items() if k in valid_keys}
                    return cls(**filtered_data)
            except Exception:
                pass
        return cls()

DEFAULT_CONFIG = InterlinearConfig.load()
