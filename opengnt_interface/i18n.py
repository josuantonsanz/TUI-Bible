import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

class TranslationManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TranslationManager, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
            
        self.current_language = "en"
        self.translations: Dict[str, Dict[str, str]] = {}
        self.base_path = Path(__file__).parent / "translations"
        self.initialized = True
        self.load_translations("en")
        self.load_translations("es")

    def load_translations(self, lang_code: str):
        file_path = self.base_path / f"{lang_code}.json"
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.translations[lang_code] = json.load(f)
            except Exception as e:
                print(f"Error loading translations for {lang_code}: {e}")
                self.translations[lang_code] = {}
        else:
            self.translations[lang_code] = {}

    def set_language(self, lang_code: str):
        if lang_code not in self.translations:
            self.load_translations(lang_code)
        self.current_language = lang_code

    def get_text(self, key: str, default: Optional[str] = None) -> str:
        # Try current language
        lang_dict = self.translations.get(self.current_language, {})
        text = lang_dict.get(key)
        
        if text is not None:
            return text
            
        # Fallback to English
        if self.current_language != "en":
            en_dict = self.translations.get("en", {})
            text = en_dict.get(key)
            if text is not None:
                return text
                
        # Return default or key itself
        return default if default is not None else key

# Singleton instance
manager = TranslationManager()

def _(key: str, default: Optional[str] = None) -> str:
    """Shortcut for get_text."""
    return manager.get_text(key, default)

def set_language(lang_code: str):
    """Shortcut for set_language."""
    manager.set_language(lang_code)
