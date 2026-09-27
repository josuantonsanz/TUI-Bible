import sys
import shutil
import unicodedata
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.align import Align
from rich.style import Style

from textual import events
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Label, TextArea, Button, Switch, Input, TabbedContent, TabPane, Select
from textual.containers import Vertical, Horizontal, Grid, ScrollableContainer
from textual.binding import Binding
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Reuse existing repositories and services
from opengnt_interface.repositories import TextRepository, TranslationRepository, VariantRepository, AnnotationRepository
from opengnt_interface.services import TranslationService, VariantService, InterlinearService, AnnotationService, DictionaryService, ParallelPassageService, InterlinearVerse, InterlinearWord
from opengnt_interface.config import DEFAULT_CONFIG
from opengnt_interface.morphology import expand_morphology
from opengnt_interface.bible_books import parse_reference, get_standard_name, get_standard_abbr, find_book_id
from opengnt_interface.i18n import _, set_language
from opengnt_interface.paths import backups_directory, database_path, dictionary_path

# Apply language from config
set_language(DEFAULT_CONFIG.language)

def translate_reference(ref: str, use_abbr: bool = False) -> str:
    """Translates the book part of a reference string."""
    if not ref: return ""
    book_id, chapter, verse = parse_reference(ref)
    if book_id is not None:
        if use_abbr:
            book_name = get_standard_abbr(book_id, DEFAULT_CONFIG.language)
        else:
            book_name = get_standard_name(book_id, DEFAULT_CONFIG.language)
        
        if chapter is not None:
             if verse is not None:
                 return f"{book_name} {chapter}:{verse}"
             return f"{book_name} {chapter}"
        return book_name
    return ref

# --- State Management ---

class OpenGNTState:
    """Helper class to manage DB connection and business logic state."""
    def __init__(self, book_name="John", chapter=1, verse=1):
        self.book_name = book_name
        self.chapter = chapter
        self.verse = verse
        self.current_verse_data: Optional[InterlinearVerse] = None
        
        db_path = database_path()
        dict_path = dictionary_path()
        parallels_path = Path(__file__).parent / "data" / "parallels.json"

        self.engine = create_engine(f'sqlite:///{db_path}')
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        
        self.text_repo = TextRepository(self.session)
        self.trans_repo = TranslationRepository(self.session)
        self.variant_repo = VariantRepository(self.session)
        self.anno_repo = AnnotationRepository(self.session)
        
        self.trans_service = TranslationService(self.trans_repo, self.text_repo)
        self.variant_service = VariantService(self.variant_repo, self.text_repo)
        self.anno_service = AnnotationService(self.anno_repo, self.text_repo)
        self.dict_service = DictionaryService(str(dict_path))
        self.parallel_service = ParallelPassageService(str(parallels_path))
        self.interlinear_service = InterlinearService(self.text_repo, self.trans_service, self.variant_service, self.parallel_service)

    def load_verse(self) -> str:
        """Loads data and returns a status message."""
        book = self.text_repo.get_book_by_name(self.book_name)
        if not book:
            return _("error_book_not_found").format(book=self.book_name)
            
        self.current_verse_data = self.interlinear_service.get_verse_data(
            book.id, self.chapter, self.verse
        )
        
        if not self.current_verse_data:
            return _("verse_not_found").format(ref=f"{self.book_name} {self.chapter}:{self.verse}")
            
        return f"{_('loaded')} {self.current_verse_data.reference}"

    def next_verse(self):
        self.verse += 1
        return self.load_verse()

    def prev_verse(self):
        if self.verse > 1:
            self.verse -= 1
        return self.load_verse()

# --- Screens ---

class HelpScreen(ModalScreen):
    """Screen for displaying help and keybindings."""
    CSS = """
    HelpScreen {
        align: center middle;
        background: rgba(0,0,0,0.5);
    }
    
    #help-dialog {
        width: 70;
        height: auto;
        max-height: 80%;
        background: #cecdc3;
        border: thick #100f0f;
        padding: 0 2;
    }
    
    #help-title {
        text-align: center;
        text-style: bold;
        padding-bottom: 0;
        border-bottom: solid #100f0f;
        margin-bottom: 0;
    }
    
    .help-section {
        margin-top: 0;
        text-style: bold;
        color: #ad8301;
    }
    
    .help-row {
        height: auto;
        margin-left: 2;
    }
    
    .key {
        width: 15;
        text-style: bold;
        color: #bc5215;
    }
    
    .desc {
        width: 1fr;
    }
    
    #help-content {
        height: 1fr;
        overflow-y: auto;
        padding-right: 1;
    }
    
    #help-close {
        height: 3;
        margin-top: 0;
        align: center middle;
    }
    """
    
    def compose(self) -> ComposeResult:
        with Vertical(id="help-dialog"):
            yield Label(_("commands_shortcuts"), id="help-title")
            
            with ScrollableContainer(id="help-content"):
                yield Label(_("main_navigation"), classes="help-section")
                with Horizontal(classes="help-row"):
                    yield Label("Q", classes="key")
                    yield Label(_("quit_app"), classes="desc")
                with Horizontal(classes="help-row"):
                    yield Label("↑ / ↓", classes="key")
                    yield Label(_("next_verse"), classes="desc")
                with Horizontal(classes="help-row"):
                    yield Label("← / →", classes="key")
                    yield Label(_("next_word"), classes="desc")
                with Horizontal(classes="help-row"):
                    yield Label("G", classes="key")
                    yield Label(_("goto_reference"), classes="desc")
                with Horizontal(classes="help-row"):
                    yield Label("B", classes="key")
                    yield Label(_("backup_database"), classes="desc")
                
                yield Label(_("editing_actions"), classes="help-section")
                with Horizontal(classes="help-row"):
                    yield Label("a", classes="key")
                    yield Label(_("edit_word_ann"), classes="desc")
                with Horizontal(classes="help-row"):
                    yield Label("A", classes="key")
                    yield Label(_("edit_lemma_ann"), classes="desc")
                with Horizontal(classes="help-row"):
                    yield Label("v / V", classes="key")
                    yield Label(_("edit_verse_ann"), classes="desc")
                with Horizontal(classes="help-row"):
                    yield Label("t", classes="key")
                    yield Label(_("edit_word_trans"), classes="desc")
                with Horizontal(classes="help-row"):
                    yield Label("T", classes="key")
                    yield Label(_("edit_lemma_trans"), classes="desc")
                with Horizontal(classes="help-row"):
                    yield Label("Ctrl+E", classes="key")
                    yield Label(_("gnt_tools"), classes="desc")
                with Horizontal(classes="help-row"):
                    yield Label("p", classes="key")
                    yield Label(_("focus_phrase"), classes="desc")
                with Horizontal(classes="help-row"):
                    yield Label(",", classes="key")
                    yield Label(_("show_settings"), classes="desc")
                with Horizontal(classes="help-row"):
                    yield Label("h", classes="key")
                    yield Label(_("show_help"), classes="desc")
                with Horizontal(classes="help-row"):
                    yield Label("c", classes="key")
                    yield Label(_("show_concordance"), classes="desc")
                with Horizontal(classes="help-row"):
                    yield Label("d", classes="key")
                    yield Label(_("show_dictionary"), classes="desc")

                yield Label(_("in_modals_editors"), classes="help-section")
                with Horizontal(classes="help-row"):
                    yield Label("Ctrl+S", classes="key")
                    yield Label(_("save_close"), classes="desc")
                with Horizontal(classes="help-row"):
                    yield Label("Escape", classes="key")
                    yield Label(_("cancel_close"), classes="desc")
                with Horizontal(classes="help-row"):
                    yield Label("Enter (Phrase)", classes="key")
                    yield Label(_("save_phrase"), classes="desc")

            with Horizontal(id="help-close"):
                yield Button(_("close"), variant="primary", id="close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()

    def key_escape(self):
        self.dismiss()

class AnnotationTextArea(TextArea):
    """Custom TextArea that handles Ctrl+Enter and Ctrl+S for saving."""
    async def _on_key(self, event):
        if event.key == "ctrl+enter" or event.key == "ctrl+s":
            event.stop()
            event.prevent_default()
            if hasattr(self.screen, "action_save"):
                self.screen.action_save()
        else:
            await super()._on_key(event)

class AnnotationEditorScreen(ModalScreen[str]):
    """Screen for editing annotations."""
    
    CSS = """
    AnnotationEditorScreen {
        align: center middle;
        background: rgba(0,0,0,0.5);
    }
    
    #editor-dialog {
        width: 80%;
        height: 60%;
        background: #cecdc3;
        border: thick #100f0f;
        padding: 1 2;
        layout: vertical;
    }
    
    #editor-title {
        text-align: center;
        text-style: bold;
        padding-bottom: 1;
    }
    
    TextArea {
        height: 1fr;
        border: solid #100f0f;
        margin-bottom: 1;
    }
    
    #editor-buttons {
        height: 3;
        align: center middle;
    }
    
    Button {
        margin: 0 1;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+enter", "save", "Save", priority=True),
        Binding("ctrl+s", "save", "Save", priority=True),
    ]
    
    def __init__(self, title: str, initial_text: str):
        super().__init__()
        self.dialog_title = title
        self.initial_text = initial_text
        
    def compose(self) -> ComposeResult:
        with Vertical(id="editor-dialog"):
            yield Label(self.dialog_title, id="editor-title")
            yield AnnotationTextArea(self.initial_text, id="annotation-input")
            with Horizontal(id="editor-buttons"):
                yield Button(_("save"), variant="primary", id="save")
                yield Button(_("cancel"), variant="error", id="cancel")
    
    def on_mount(self):
        self.query_one(TextArea).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.action_save()
        else:
            self.dismiss(None)

    def action_save(self) -> None:
        self.dismiss(self.query_one("#annotation-input", TextArea).text)
            
            
    def key_escape(self):
        self.dismiss(None)

class GoToScreen(ModalScreen[str]):
    """Screen for navigation."""
    
    CSS = """
    GoToScreen {
        align: center middle;
        background: rgba(0,0,0,0.5);
    }
    
    #goto-dialog {
        width: 60;
        height: 15;
        background: #cecdc3;
        border: thick #100f0f;
        padding: 1 2;
    }
    
    Label {
        padding-bottom: 1;
        text-style: bold;
    }
    
    Input {
        margin-bottom: 1;
    }
    
    #buttons {
        align: center middle;
    }
    
    Button {
        margin: 0 1; 
    }
    """
    
    BINDINGS = [
        Binding("ctrl+enter", "submit", "Go", priority=True),
        Binding("ctrl+s", "submit", "Go", priority=True),
        Binding("ctrl+j", "submit", "Go", show=False, priority=True),
    ]
    
    
    def compose(self) -> ComposeResult:
        with Vertical(id="goto-dialog"):
            yield Label(_("go_to_ref_placeholder"))
            yield Input(placeholder=_("book_ch_vs_placeholder"), id="ref-input")
            with Horizontal(id="buttons"):
                yield Button(_("go"), variant="primary", id="go")
                yield Button(_("cancel"), variant="error", id="cancel")
    
    def on_mount(self):
        self.query_one("Input").focus()
        
    def on_input_submitted(self, event):
        self.dismiss(event.value)
        
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "go":
            self.action_submit()
        else:
            self.dismiss(None)

    def action_submit(self) -> None:
        self.dismiss(self.query_one("#ref-input", Input).value)
            

    def key_escape(self):
        self.dismiss(None)

class SettingsScreen(Screen):
    """Screen for managing application settings."""
    
    CSS = """
    SettingsScreen {
        background: #cecdc3;
        color: #100f0f;
    }
    
    #settings-container {
        height: 100%;
        width: 100%;
    }
    
    .settings-column {
        width: 1fr;
        height: 100%;
        padding: 1 2;
    }
    
    #left-col {
        border-right: solid #100f0f;
    }
    
    #settings-title {
        text-align: center;
        text-style: bold;
        padding-bottom: 1;
        border-bottom: solid #100f0f;
        margin-bottom: 1;
    }
    
    .setting-row {
        height: 3;
        align: left middle;
        padding: 0 1;
        border-bottom: solid #e6e4d9 10%;
    }
    
    .setting-label {
        width: 1fr;
        padding-top: 1;
        color: #100f0f;
    }
    
    Switch {
        width: auto;
        background: #cecdc3;
        color: #100f0f;
        border: none;
    }

    Switch > .switch--slider {
        color: #b4b19c; /* Off state */
    }

    Switch.-on > .switch--slider {
        color: #66800b; /* On state (Flexoki Green) */
    }

    Switch > .switch--thumb {
        background: #fff;
        color: #100f0f;
    }
    
    #settings-buttons {
        margin-top: 1;
        align: center middle;
    }
    """
    
    def compose(self) -> ComposeResult:
        langs = [(_("english"), "en"), (_("spanish"), "es")]
        
        with Horizontal(id="settings-container"):
            # Left Column: General Configuration
            with Vertical(id="left-col", classes="settings-column"):
                yield Label(_("settings"), id="settings-title")
                
                with Horizontal(classes="setting-row"):
                    yield Label(_("show_strongs"), classes="setting-label")
                    yield Switch(value=DEFAULT_CONFIG.show_strongs, id="show_strongs")
                    
                with Horizontal(classes="setting-row"):
                    yield Label(_("show_morphology"), classes="setting-label")
                    yield Switch(value=DEFAULT_CONFIG.show_morphology, id="show_morphology")
                    
                with Horizontal(classes="setting-row"):
                    yield Label(_("show_lemma"), classes="setting-label")
                    yield Switch(value=DEFAULT_CONFIG.show_lemma, id="show_lemma")
                    
                with Horizontal(classes="setting-row"):
                    yield Label(_("show_verse_ann"), classes="setting-label")
                    yield Switch(value=DEFAULT_CONFIG.show_verse_annotations, id="show_verse_annotations")
                    
                with Horizontal(classes="setting-row"):
                    yield Label(_("show_spanish_trans"), classes="setting-label")
                    yield Switch(value=DEFAULT_CONFIG.show_spanish_translation, id="show_spanish_translation")
                        
                with Horizontal(classes="setting-row"):
                    yield Label(_("show_latin_trans"), classes="setting-label")
                    yield Switch(value=DEFAULT_CONFIG.show_latin_translation, id="show_latin_translation")

                with Horizontal(classes="setting-row"):
                    yield Label(_("show_dict_panel"), classes="setting-label")
                    yield Switch(value=DEFAULT_CONFIG.show_dictionary_panel, id="show_dictionary_panel")

                with Horizontal(classes="setting-row"):
                    yield Label(_("show_instance_trans"), classes="setting-label")
                    yield Switch(value=DEFAULT_CONFIG.show_translation, id="show_translation")
                
                with Horizontal(classes="setting-row"):
                    yield Label(_("language"), classes="setting-label")
                    yield Select(langs, value=DEFAULT_CONFIG.language, id="language")

            # Right Column: Stylometry
            with Vertical(id="right-col", classes="settings-column"):
                yield Label("Stylometry Analytics", id="stylometry-title")
                
                with Horizontal(classes="setting-row"):
                    yield Label(_("enable_stylometry_colors"), classes="setting-label")
                    yield Switch(value=DEFAULT_CONFIG.show_stylometry, id="show_stylometry")
                    
                # Stylometry Legends
                with Vertical(id="legends-container"):
                    # Gospels Legend
                    with Horizontal(classes="setting-row"):
                        yield Label(
                            f"  [b]{_('stylometry_legend')}[/b] "
                            f"[bold #000000 on #4a90e2] {_('matthew')} [/] "
                            f"[bold #000000 on #e24a4a] {_('mark')} [/] "
                            f"[bold #000000 on #4ae257] {_('luke')} [/] "
                            f"[bold #000000 on #e2c84a] {_('john')} [/]", 
                            classes="setting-label",
                            id="stylometry-legend"
                        )

                    # Pauline Stylometry Legend
                    with Horizontal(classes="setting-row"):
                        yield Label(
                            f"  [b]{_('pauline_legend')}[/b] "
                            f"[bold #000000 on #b1cae8] {_('paul_legend')} [/] "
                            f"[bold #000000 on #e3d9aa] {_('epistle_legend')} [/] "
                            f"[bold #000000 on #8fb065] {_('both_legend')} [/] ", 
                            classes="setting-label",
                            id="pauline-legend"
                        )

                    # Johannine Stylometry Legend
                    with Horizontal(classes="setting-row"):
                        yield Label(
                            f"  [b]{_('johannine_legend')}[/b] "
                            f"[bold #000000 on #b1cae8] {_('john')} [/] "
                            f"[bold #000000 on #e3d9aa] {_('john_epistle')} [/] "
                            f"[bold #000000 on #8fb065] {_('both_legend')} [/] ", 
                            classes="setting-label",
                            id="johannine-legend"
                        )

                    # Catholic Epistles Legend
                    with Horizontal(classes="setting-row"):
                        yield Label(
                            f"  [b]{_('catholic_legend')}[/b] "
                            f"[bold #000000 on #4a90e2] {_('general_legend')} [/]", 
                            classes="setting-label",
                            id="catholic-legend"
                        )
            
                with Horizontal(id="settings-buttons"):
                    yield Button(_("close"), variant="primary", id="close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "language" and event.value:
            DEFAULT_CONFIG.language = event.value
            set_language(event.value)
            DEFAULT_CONFIG.save()
            self.app.action_refresh_view()

    def on_switch_changed(self, event: Switch.Changed) -> None:
        if event.switch.id == "show_strongs":
            DEFAULT_CONFIG.show_strongs = event.value
        elif event.switch.id == "show_morphology":
            DEFAULT_CONFIG.show_morphology = event.value
        elif event.switch.id == "show_lemma":
            DEFAULT_CONFIG.show_lemma = event.value
        elif event.switch.id == "show_verse_annotations":
            DEFAULT_CONFIG.show_verse_annotations = event.value
        elif event.switch.id == "show_spanish_translation":
            DEFAULT_CONFIG.show_spanish_translation = event.value
        elif event.switch.id == "show_latin_translation":
            DEFAULT_CONFIG.show_latin_translation = event.value
        elif event.switch.id == "show_dictionary_panel":
            DEFAULT_CONFIG.show_dictionary_panel = event.value
        elif event.switch.id == "show_stylometry":
            DEFAULT_CONFIG.show_stylometry = event.value
        elif event.switch.id == "show_translation":
            DEFAULT_CONFIG.show_translation = event.value
            
        # Persistence
        DEFAULT_CONFIG.save()

        # Notify the app that settings changed
        self.app.action_refresh_view()

    def key_escape(self):
        self.dismiss()

class TranslationEditorScreen(ModalScreen[str]):
    """Screen for editing translations."""
    
    CSS = """
    TranslationEditorScreen {
        align: center middle;
        background: rgba(0,0,0,0.5);
    }
    
    #trans-dialog {
        width: 80%;
        height: auto;
        background: #cecdc3;
        border: thick #100f0f;
        padding: 1 2;
    }
    
    #trans-title {
        text-align: center;
        text-style: bold;
        padding-bottom: 1;
    }

    #morph-info {
        text-align: center;
        color: #66800b;
        padding-bottom: 1;
    }
    
    Input {
        margin-bottom: 1;
    }
    
    #trans-buttons {
        height: 3;
        align: center middle;
    }
    
    Button {
        margin: 0 1; 
    }
    """
    
    BINDINGS = [
        Binding("ctrl+enter", "submit", "Save", priority=True),
        Binding("ctrl+s", "submit", "Save", priority=True),
        Binding("ctrl+j", "submit", "Save", show=False, priority=True),
    ]
    
    def __init__(self, title: str, morph_info: str, initial_text: str):
        super().__init__()
        self.dialog_title = title
        self.morph_info = morph_info
        self.initial_text = initial_text
        
    def compose(self) -> ComposeResult:
        with Vertical(id="trans-dialog"):
            yield Label(self.dialog_title, id="trans-title")
            if self.morph_info:
                yield Label(self.morph_info, id="morph-info")
            yield Input(value=self.initial_text, id="trans-input")
            with Horizontal(id="trans-buttons"):
                yield Button(_("save"), variant="primary", id="save")
                yield Button(_("cancel"), variant="error", id="cancel")
    
    def on_mount(self):
        self.query_one("Input").focus()

    def on_input_submitted(self, event):
        self.dismiss(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.action_submit()
        else:
            self.dismiss(None)

    def action_submit(self) -> None:
        self.dismiss(self.query_one("#trans-input", Input).value)
            
            
    def key_escape(self):
        self.dismiss(None)

class GreekWordEditorScreen(ModalScreen[dict]):
    """Screen for editing Greek word properties."""
    
    CSS = """
    GreekWordEditorScreen {
        align: center middle;
        background: rgba(0,0,0,0.5);
    }
    
    #greek-editor-dialog {
        width: 60;
        height: auto;
        background: #cecdc3;
        border: thick #100f0f;
        padding: 1 2;
    }
    
    #editor-title {
        text-align: center;
        text-style: bold;
        padding-bottom: 1;
        border-bottom: solid #100f0f;
        margin-bottom: 1;
    }
    
    Label {
        padding-bottom: 0;
        margin-top: 1;
        color: #100f0f;
    }
    
    Input {
        height: 3;
        margin-bottom: 0;
        border: solid #100f0f;
    }
    
    #editor-buttons {
        margin-top: 2;
        align: center middle;
    }
    
    Button {
        margin: 0 1; 
    }
    """
    
    def __init__(self, title: str, word_data: dict):
        super().__init__()
        self.dialog_title = title
        self.word_data = word_data
        
    def compose(self) -> ComposeResult:
        with Vertical(id="greek-editor-dialog"):
            yield Label(self.dialog_title, id="editor-title")
            
            yield Label("Greek Text (Accented):")
            yield Input(value=self.word_data.get('greek_accented', ''), id="greek-accented")
            
            yield Label("Lexeme:")
            yield Input(value=self.word_data.get('lexeme', ''), id="lexeme")
            
            yield Label("RMAC (Morphology):")
            yield Input(value=self.word_data.get('rmac', ''), id="rmac")
            
            yield Label(_("strongs_number"))
            yield Input(value=self.word_data.get('strongs', ''), id="strongs")
            
            with Horizontal(id="editor-buttons"):
                yield Button(_("save"), variant="primary", id="save")
                yield Button(_("cancel"), variant="error", id="cancel")
    
    def on_mount(self):
        self.query_one("#greek-accented", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.action_submit()
        else:
            self.dismiss(None)

    def action_submit(self) -> None:
        from textual.widgets import Input
        result = {
            'greek_accented': self.query_one("#greek-accented", Input).value,
            'lexeme': self.query_one("#lexeme", Input).value,
            'rmac': self.query_one("#rmac", Input).value,
            'strongs': self.query_one("#strongs", Input).value,
        }
        self.dismiss(result)
            
    def key_escape(self):
        self.dismiss(None)

class PunctuationEditorScreen(ModalScreen[dict]):
    """Screen for editing word punctuation."""
    
    CSS = """
    PunctuationEditorScreen {
        align: center middle;
        background: rgba(0,0,0,0.5);
    }
    
    #punct-editor-dialog {
        width: 40;
        height: auto;
        background: #cecdc3;
        border: thick #100f0f;
        padding: 1 2;
    }
    
    #editor-title {
        text-align: center;
        text-style: bold;
        padding-bottom: 1;
        border-bottom: solid #100f0f;
        margin-bottom: 1;
    }
    
    Label {
        padding-bottom: 0;
        margin-top: 1;
        color: #100f0f;
    }
    
    Input {
        height: 3;
        margin-bottom: 0;
        border: solid #100f0f;
    }
    
    #editor-buttons {
        margin-top: 2;
        align: center middle;
    }
    
    Button {
        margin: 0 1; 
    }
    """
    
    def __init__(self, title: str, punct_before: str, punct_after: str):
        super().__init__()
        self.dialog_title = title
        self.punct_before = punct_before
        self.punct_after = punct_after
        
    def compose(self) -> ComposeResult:
        with Vertical(id="punct-editor-dialog"):
            yield Label(self.dialog_title, id="editor-title")
            
            yield Label("Punctuation Before:")
            yield Input(value=self.punct_before, id="punct-before")
            
            yield Label(_("punctuation_after"))
            yield Input(value=self.punct_after, id="punct-after")
            
            with Horizontal(id="editor-buttons"):
                yield Button(_("save"), variant="primary", id="save")
                yield Button(_("cancel"), variant="error", id="cancel")
    
    def on_mount(self):
        self.query_one("#punct-after", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.action_submit()
        else:
            self.dismiss(None)

    def action_submit(self) -> None:
        from textual.widgets import Input
        result = {
            'before': self.query_one("#punct-before", Input).value,
            'after': self.query_one("#punct-after", Input).value,
        }
        self.dismiss(result)
            
    def key_escape(self):
        self.dismiss(None)

class GreekToolsMenu(ModalScreen[str]):
    """Horizontal toolbar for Greek text editing tools."""
    
    CSS = """
    GreekToolsMenu {
        align: center bottom;
        background: rgba(0,0,0,0.1);
    }
    
    #tools-container {
        width: 100%;
        height: 6;
        background: #cecdc3;
        border-top: thick #100f0f;
        layout: horizontal;
        padding: 0 1;
        align: center middle;
    }
    
    .tool-button {
        margin: 0 1;
        min-width: 8;
        background: #e6e4d9;
        color: #100f0f;
        height: 3;
        border: none;
    }
    
    .tool-button:hover {
        background: #ad8301;
        color: #fff;
    }

    .tool-button.-error:hover {
        background: #e43444;
    }
    
    #tools-title {
        width: auto;
        padding: 0 2;
        text-style: bold;
        color: #bc5215;
    }
    """
    
    def __init__(self, word_text: str):
        super().__init__()
        self.word_text = word_text
        
    def compose(self) -> ComposeResult:
        with Horizontal(id="tools-container"):
            yield Label(f"[b]{self.word_text}[/]", id="tools-title")
            
            yield Button(_("edit"), classes="tool-button", id="edit_info")
            yield Button(_("move_l"), classes="tool-button", id="move_left")
            yield Button(_("move_r"), classes="tool-button", id="move_right")
            yield Button(_("add"), classes="tool-button", id="add_after")
            yield Button(_("prepend"), classes="tool-button", id="add_before")
            yield Button(_("punct"), classes="tool-button", id="edit_punct")
            yield Button(_("delete"), variant="error", id="remove_word", classes="tool-button")
            yield Button(_("close"), variant="primary", id="close", classes="tool-button")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close":
            self.dismiss(None)
        else:
            self.dismiss(event.button.id)
            
    def key_e(self): self.dismiss("edit_info")
    def key_l(self): self.dismiss("move_left")
    def key_r(self): self.dismiss("move_right")
    def key_a(self): self.dismiss("add_after")
    def key_p(self): self.dismiss("add_before")
    def key_full_stop(self): self.dismiss("edit_punct")
    def key_delete(self): self.dismiss("remove_word")
    def key_escape(self): self.dismiss(None)

class ConcordanceScreen(ModalScreen):
    """Screen for displaying lemma concordance."""
    
    CSS = """
    ConcordanceScreen {
        align: center middle;
        background: rgba(0,0,0,0.5);
    }
    
    #concordance-dialog {
        width: 90%;
        height: 85%;
        background: #cecdc3;
        border: thick #100f0f;
        padding: 1 1;
    }
    
    #concordance-title {
        text-align: center;
        text-style: bold;
        padding-bottom: 0;
        margin-bottom: 0;
        color: #100f0f;
    }
    
    #concordance-content {
        height: 1fr;
        padding-right: 1;
    }

    TabbedContent {
        height: 1fr;
        margin-top: 1;
        color: #100f0f;
    }

    TabbedContent Tabs {
        color: #100f0f;
    }

    TabPane {
        padding: 0 1;
    }
    
    .form-group {
        height: auto;
        margin-top: 1;
    }

    .form-header-row {
        height: auto;
        margin-bottom: 0;
    }
    
    .form-header {
        text-style: bold;
        color: #100f0f;
    }
    
    .form-morph {
        color: #66800b;
    }
    
    .translation-group {
        height: auto;
        margin-left: 2;
        margin-top: 0;
        margin-bottom: 0;
    }
    
    .occ-line {
        height: auto;
        width: 1fr;
    }

    .book-header {
        text-style: bold;
        color: #ad8301;
        background: #e6e4d9;
        padding: 0 1;
        margin-top: 1;
    }

    .ref-link {
        color: #bc5215;
        text-style: underline;
    }

    TabbedContent Tabs {
        color: #100f0f !important;
    }

    /* Target individual tabs by their auto-generated IDs */
    #--content-tab-tab-inflection {
        color: #100f0f !important;
    }

    #--content-tab-tab-book {
        color: #100f0f !important;
    }

    ConcordanceStatic {
    }

    Tooltip {
        background: #100f0f;
        color: #fffaf3;
        border: solid #66800b;
        padding: 0 1;
    }

    #concordance-close {
        height: 3;
        align: center middle;
        margin-top: 1;
    }
    """
    
    def __init__(self, data: dict):
        super().__init__()
        self.concordance_data = data
        
    def compose(self) -> ComposeResult:
        with Vertical(id="concordance-dialog"):
            lemma = self.concordance_data['lemma']
            lt = self.concordance_data.get('lemma_translation', '')
            count = self.concordance_data.get('total_count', 0)
            formatted_lt = lt.capitalize() if lt else ""
            yield Label(f"{_('concordance_title')}: {lemma} ({count}) {formatted_lt}", id="concordance-title")
            
            with TabbedContent():
                with TabPane(_("by_inflection"), id="tab-inflection"):
                    with ScrollableContainer():
                        # Sort groups by surface form for readability
                        sorted_keys = sorted(self.concordance_data['by_inflection'].keys())
                        for key in sorted_keys:
                            group_data = self.concordance_data['by_inflection'][key]
                            trans_groups = group_data['translation_groups']
                            expanded_morph = group_data['expanded_morph']
                            form, morph = key
                            # Total count for this inflection
                            infl_count = sum(len(tg['occurrences']) for tg in trans_groups)
                            with Vertical(classes="form-group"):
                                with Horizontal(classes="form-header-row"):
                                    yield Label(f"{form} ({infl_count})", classes="form-header")
                                    yield Label(f" ({morph} - {expanded_morph})", classes="form-morph")
                                
                                for tg in trans_groups:
                                    # Use Static for proper wrapping with Rich markup
                                    trans_text = tg['translation'] or "---"
                                    
                                    # Build clickable references string
                                    # Group occs by book for the display
                                    book_map = {}
                                    for o in tg['occurrences']:
                                        if o['book_label'] not in book_map:
                                            book_map[o['book_label']] = []
                                        book_map[o['book_label']].append(o)
                                    
                                    parts = []
                                    for b_lbl, occs in book_map.items():
                                        book_name = translate_reference(occs[0]['book_name'], use_abbr=True)
                                        ref_links = []
                                        for o in occs:
                                            # We need to escape the ref for the @click tag
                                            nav_ref = o['ref_str']
                                            disp_ref = f"{o['chapter']}:{o['verse']}"
                                            ref_links.append(f"[@click=\"app.goto_ref_and_close('{nav_ref}')\"]{disp_ref}[/]")
                                        
                                        parts.append(f"{book_name} ([b]{len(occs)}[/]) {'; '.join(ref_links)}")
                                    
                                    refs_markup = ". ".join(parts)
                                    trans_count = len(tg['occurrences'])
                                    markup = f"[#bc5215][b]{trans_text} ({trans_count})[/][/] [#ad8301]{refs_markup}[/]"
                                    yield ReferenceStatic(markup, classes="occ-line translation-group")

                with TabPane(_("by_book"), id="tab-book"):
                    with ScrollableContainer():
                        by_book = self.concordance_data['by_book']
                        # Sort books by their biblical order
                        sorted_books = sorted(by_book.keys(), key=lambda x: by_book[x]['order'])
                        
                        for b_name in sorted_books:
                            # Calculate total occurrences in this book for this lemma
                            book_total = sum(len(occs) for infl in by_book[b_name]['inflections'].values() for occs in infl['translations'].values())
                            translated_name = translate_reference(b_name, use_abbr=True)
                            
                            # Calculate relative frequency if total_words is available
                            total_words = by_book[b_name].get('total_words', 0)
                            rel_freq_str = ""
                            if total_words > 0:
                                rel_freq = (book_total / total_words) * 10000
                                rel_freq_str = f" [{rel_freq:.1f} {_('per_10k')}]"
                                
                            yield Label(f" {translated_name} ({book_total}){rel_freq_str} ", classes="book-header")
                            inflections = by_book[b_name]['inflections']
                            
                            # Sort inflections by form
                            sorted_infl_keys = sorted(inflections.keys())
                            for key in sorted_infl_keys:
                                infl_data = inflections[key]
                                # Count for this inflection in THIS book
                                infl_book_count = sum(len(occs) for occs in infl_data['translations'].values())
                                form, morph = key
                                with Vertical(classes="form-group"):
                                    with Horizontal(classes="form-header-row"):
                                        yield Label(f" {form} ({infl_book_count})", classes="form-header")
                                        yield Label(f" ({morph})", classes="form-morph")
                                    
                                    for trans, occs in infl_data['translations'].items():
                                        ref_links = []
                                        for o in occs:
                                            nav_ref = o['ref_str']
                                            disp_ref = f"{o['chapter']}:{o['verse']}"
                                            ref_links.append(f"[@click=\"app.goto_ref_and_close('{nav_ref}')\"]{disp_ref}[/]")
                                        
                                        refs_markup = ", ".join(ref_links)
                                        markup = f"[#bc5215][b]{trans}[/][/] [#ad8301]{refs_markup}[/]"
                                        yield ReferenceStatic(markup, classes="occ-line translation-group")
            
            with Horizontal(id="concordance-close"):
                yield Button(_("close"), variant="primary", id="close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()

    def key_escape(self):
        self.dismiss()

class DictionaryScreen(ModalScreen):
    """Screen for displaying Abbott-Smith dictionary entry."""
    
    CSS = """
    DictionaryScreen {
        align: center middle;
        background: rgba(0,0,0,0.5);
    }
    
    #dictionary-dialog {
        width: 80%;
        height: 70%;
        background: #cecdc3;
        border: thick #100f0f;
        padding: 1 2;
    }
    
    #dictionary-title {
        text-align: center;
        text-style: bold;
        padding-bottom: 1;
        border-bottom: solid #100f0f;
        margin-bottom: 1;
        color: #100f0f;
    }
    
    #dictionary-content {
        height: 1fr;
        overflow-y: auto;
        padding-right: 1;
    }
    
    #dictionary-close {
        height: 3;
        align: center middle;
        margin-top: 1;
    }
    """
    
    def __init__(self, lemma: str, definition_text):
        super().__init__()
        self.lemma = lemma
        self.definition_text = definition_text
        
    def compose(self) -> ComposeResult:
        with Vertical(id="dictionary-dialog"):
            yield Label(f"Abbott-Smith: {self.lemma}", id="dictionary-title")
            with ScrollableContainer(id="dictionary-content"):
                yield Static(self.definition_text)
            
            with Horizontal(id="dictionary-close"):
                yield Button(_("close"), variant="primary", id="close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()

    def key_escape(self):
        self.dismiss()

class ReferenceStatic(Static):
    """Custom Static for text with clickable references that shows a verse preview on hover."""
    
    def on_mouse_move(self, event: events.MouseMove) -> None:
        """Handle mouse movement to show verse preview tooltip."""
        try:
            style = self.get_style_at(event.x, event.y)
        except Exception:
            return

        if style and style.meta:
            # Look for navigation links (Textual uses "@click" for the attribute)
            click_action = style.meta.get("@click")
            if click_action:
                import re
                # Match any action that takes a reference as first argument: goto_ref, goto_ref_and_close, etc.
                match = re.search(r"\w+\(['\"]([^'\"]+)['\"]\)", str(click_action))
                if match:
                    ref = match.group(1)
                    if hasattr(self, "_last_ref") and self._last_ref == ref:
                        return
                    self._last_ref = ref

                    try:
                        from .bible_books import parse_reference as parse_ref
                        book_id, chap, ver = parse_ref(ref)
                        if book_id is not None and chap is not None and ver is not None:
                            # 1. Try phrasing translation first (Priority)
                            phrases = self.app.state.trans_service.translation_repo.get_phrase_translations(book_id, chap, ver)
                            resolved_text = None
                            if phrases:
                                # Take the first one found (usually only one per verse in this project)
                                resolved_text = phrases[0].spanish_translation
                            
                            # 2. Fallback to default Spanish if no phrase translation
                            if not resolved_text:
                                resolved_text, _ = self.app.state.text_repo.get_verse_translation(book_id, chap, ver)

                            if resolved_text:
                                self.tooltip = resolved_text
                            else:
                                self.tooltip = f"({ref}) No translation found."
                        else:
                            self.tooltip = f"Could not parse ref: {ref}"
                    except Exception:
                        self.tooltip = None
                return 
        
        if hasattr(self, "_last_ref"):
            delattr(self, "_last_ref")
            self.tooltip = None

class SearchScreen(ModalScreen):
    """Screen for global search."""
    
    CSS = """
    SearchScreen {
        align: center top;
        background: rgba(0,0,0,0.5);
    }
    
    #search-dialog {
        width: 60%;
        height: 80%;
        background: #cecdc3;
        border: thick #100f0f;
        padding: 1 1;
        margin-top: 2;
    }
    
    #search-input {
        background: #e6e4d9;
        color: #100f0f;
        border: none;
        margin-bottom: 1;
    }
    
    #search-results {
        height: 1fr;
        padding-right: 1;
    }
    
    .search-result-item {
        height: auto;
        padding: 0 1;
        margin-bottom: 0;
    }
    
    .search-header {
        text-style: bold;
        color: #ad8301;
        background: #e6e4d9;
        margin-top: 1;
        padding: 0 1;
    }

    #search-status {
        color: #66800b;
        text-align: right;
        padding-bottom: 1;
    }
    
    #search-close {
        height: 3;
        align: center middle;
        margin-top: 1;
    }

    Tooltip {
        background: #100f0f;
        color: #fffaf3;
        border: solid #66800b;
        padding: 0 1;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.timer = None
        
    def compose(self) -> ComposeResult:
        with Vertical(id="search-dialog"):
            yield Input(placeholder=_("search_placeholder"), id="search-input")
            yield Label("", id="search-status")
            with ScrollableContainer(id="search-results"):
                yield Label(_("search_instructions"), id="search-instructions")
            
            with Horizontal(id="search-close"):
                yield Button(_("close"), variant="primary", id="close")

    def on_input_changed(self, event: Input.Changed) -> None:
        if self.timer:
            self.timer.stop()
        self.timer = self.set_timer(0.3, self.perform_search)
        
    def perform_search(self):
        query = self.query_one("#search-input").value.strip()
        results_container = self.query_one("#search-results")
        status_label = self.query_one("#search-status")
        
        results_container.remove_children()
        
        if len(query) < 2:
            status_label.update("")
            results_container.mount(Label(_("search_instructions")))
            return
            
        search_data = self.app.state.interlinear_service.search(query)
        results = search_data.get('results', [])
        search_type_key = search_data.get('type', 'translation')
        # Localize search type label
        search_type_label = _("greek_text_accented").replace(":", "") if search_type_key == "greek" else _("translations_title")
        
        status_label.update(_("search_found_results").format(count=len(results), type=search_type_label))
        
        if not results:
            results_container.mount(Label(_("search_no_results")))
            return
            
        # Group by book
        from itertools import groupby
        results.sort(key=lambda x: (x.get('book_order', 999), x.get('book_name')))
        
        for book_name, group in groupby(results, key=lambda x: x['book_name']):
            group_list = list(group)
            count = len(group_list)
            # Translate book name
            t_book_name = translate_reference(book_name)
            results_container.mount(Label(f"{t_book_name} ({count})", classes="search-header"))
            
            for r in group_list:
                # Format: clickable_ref -  ... snippet [match] snippet ...
                ref_link = r['ref_link'] # link text
                nav_ref = r['ref'] # navigation string
                
                # Careful with markup escaping in snippets?
                # snippet text might contain markup characters like [ or ]
                # We should escape them if we use rich markup
                from rich.markup import escape
                
                s_before = escape(r['snippet_before'])
                match_txt = escape(r['match'])
                s_after = escape(r['snippet_after'])
                
                # Highlight match
                # Use short_ref (just C:V) since we are already under a book header
                markup = f"[@click=\"app.goto_ref_and_close('{nav_ref}')\"][bold underline #bc5215]{r['short_ref']}[/][/]  [dim]...[/]{s_before}[reverse #100f0f]{match_txt}[/]{s_after}[dim]...[/]"
                
                results_container.mount(ReferenceStatic(markup, classes="search-result-item"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()

    def key_escape(self):
        self.dismiss()

class PhraseEditor(TextArea):
    """TextArea for phrase editing with custom bindings."""
    
    BINDINGS = [
        Binding("enter", "submit", "Save"),
        Binding("escape", "cancel", "Cancel"),
    ]
    
    def on_mount(self):
        # Ensure we don't have conflicting bindings if priority fails
        pass

    async def _on_key(self, event):
        # Intercept specific keys before TextArea handles them as input
        if event.key == "enter":
            event.stop()
            event.prevent_default()
            self.action_submit()
        elif event.key == "escape":
            event.stop()
            event.prevent_default()
            self.action_cancel()
        else:
            await super()._on_key(event)

    def action_submit(self):
        self.app.action_save_phrase_translation()
        
    def action_cancel(self):
        self.app.action_cancel_phrase_edit()

# --- Custom Widgets ---

class BottomMenuBar(Static):
    """A bottom menu bar displaying commands."""
    DEFAULT_CSS = """
    BottomMenuBar {
        dock: bottom;
        height: 1;
        background: #cecdc3; /* Flexoki Base-200 */
        color: #100f0f; /* Flexoki Ink */
        padding: 0 1;
    }
    """
    
    def render(self):
        # We can eventually make this dynamic or hierarchical
        return f" [bold]Q[/] {_('menu_quit')} | [bold]↑/↓[/] {_('menu_nav_verse')} | [bold]←/→[/] {_('menu_nav_word')} | [bold]Ctrl+E[/] {_('menu_gnt_tools')} | [bold]S[/] {_('search')} | [bold]C[/] {_('menu_concordance')} | [bold]D[/] {_('menu_dictionary')} | [bold]G[/] {_('menu_goto')} | [bold]B[/] {_('menu_backup')} | [bold],[/] {_('menu_settings')}"

class PhrasePanel(Static):
    """Container for the phrase translation editor."""
    DEFAULT_CSS = """
    PhrasePanel {
        dock: top;
        height: auto;
        background: #cecdc3;
        border-bottom: solid #100f0f;
        padding: 0 1;
    }
    
    Label {
        text-style: bold;
        padding-bottom: 0;
        color: #100f0f;
    }
    
    PhraseEditor {
        height: 3;
        border: none;
        background: #e6e4d9; /* Slightly lighter for input area */
        color: #100f0f; 
        margin-bottom: 0;
    }
    
    PhraseEditor:focus {
        border: none; /* Focus indicator can be subtle or handled by background */
        background: #fff;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Label(_("phrase_translation_label"), id="phrase-label")
        yield PhraseEditor(id="phrase-editor", show_line_numbers=False)

class InterlinearDisplay(Static):
    # ... (content remains similar, but we might want to update styling for Flexoki)
    
    # Using Flexoki colors for inner text
    # Greek: #100f0f (Ink)
    # Morph: #66800b (Green)
    # Strongs: #24837b (Cyan/Teal)
    # Trans: #bc5215 (Orange)
    
    """
    Widget to render the complex interlinear text.
    """
    can_focus = True
    
    current_verse_data: reactive[Optional[InterlinearVerse]] = reactive(None)
    selected_word_index: reactive[int] = reactive(0)

    def watch_current_verse_data(self, old_val, new_val):
        self.update_view()

    def watch_selected_word_index(self, old_val, new_val):
        self.update_view()
        
    def on_mount(self):
        self.update_view()
        
    def on_resize(self, event):
        self.update_view()

    def update_view(self):
        if not self.current_verse_data:
            self.update(Panel("No data loaded.", title="Interlinear"))
            return

        width = self.content_size.width or self.app.console.size.width or 80
        max_width = max(20, width - 4) 
        
        stacks = []
        for idx, word in enumerate(self.current_verse_data.words):
            pass_stack = []
            is_selected = (idx == self.selected_word_index)
            # Selection Highlight: Flexoki Base-200 bg with Ink text
            base_style = "reverse" if is_selected else ""
            
            # Greek
            pb = (word.punct_before or "").replace("<pm>", "").replace("</pm>", "").replace("¶", "").strip()
            pa = (word.punct_after or "").replace("<pm>", "").replace("</pm>", "").replace("¶", "").strip()
            clean_text = word.text.rstrip()
            greek_text = f"{pb}{clean_text}{'' if word.variants else ''}{pa}" ## I have remove the '*' symbol from the greek text, in case of variants. Time will tell if we need to add it again.
            
            style = f"bold #100f0f {base_style}" if not is_selected else "bold #100f0f reverse"

            # Apply Stylometry color if enabled and data is present and not selected
            if DEFAULT_CONFIG.show_stylometry and word.stylometry_data and not is_selected:
                book_name = getattr(self.app.state, 'book_name', '')
                book_id = find_book_id(book_name) or 0
                is_pauline_book = 45 <= book_id <= 57
                is_johannine_corpus = book_id in [43, 62, 63, 64, 66]
                is_gospel_book = 40 <= book_id <= 43
                
                # The background color of the UI without any styling
                paper_color = (242, 239, 229) # Approximate Flexoki Paper color
                
                # 1. Bivariate Pauline
                if is_pauline_book and 'pauline' in word.stylometry_data:
                    pd = word.stylometry_data['pauline']
                    p_intensity = pd.get('pauline_intensity', 0)
                    e_intensity = pd.get('epistles', {}).get(str(book_id), 0)
                    
                    # Bivariate interpolation (Blue for Pauline, Yellow/Gold for Epistle)
                    blue_color = (74, 144, 226)
                    yellow_color = (226, 200, 74)
                    
                    r = max(0, min(255, int(paper_color[0] + (blue_color[0] - paper_color[0]) * p_intensity + (yellow_color[0] - paper_color[0]) * e_intensity)))
                    g = max(0, min(255, int(paper_color[1] + (blue_color[1] - paper_color[1]) * p_intensity + (yellow_color[1] - paper_color[1]) * e_intensity)))
                    b = max(0, min(255, int(paper_color[2] + (blue_color[2] - paper_color[2]) * p_intensity + (yellow_color[2] - paper_color[2]) * e_intensity)))
                    
                    hex_color = f"#{r:02x}{g:02x}{b:02x}"
                    style = f"bold #000000 on {hex_color} {base_style}"
                
                # 2. Bivariate Johannine (1-3 John, Revelation)
                # But John Gospel (43) uses the 1D model
                elif is_johannine_corpus and book_id != 43 and 'johannine' in word.stylometry_data:
                    jd = word.stylometry_data['johannine']
                    j_intensity = jd.get('johannine_intensity', 0)
                    e_intensity = jd.get('epistles', {}).get(str(book_id), 0)
                    
                    # Same Bivariate colors (Blue for Corpus, Yellow for specifics)
                    blue_color = (74, 144, 226)
                    yellow_color = (226, 200, 74)
                    
                    r = max(0, min(255, int(paper_color[0] + (blue_color[0] - paper_color[0]) * j_intensity + (yellow_color[0] - paper_color[0]) * e_intensity)))
                    g = max(0, min(255, int(paper_color[1] + (blue_color[1] - paper_color[1]) * j_intensity + (yellow_color[1] - paper_color[1]) * e_intensity)))
                    b = max(0, min(255, int(paper_color[2] + (blue_color[2] - paper_color[2]) * j_intensity + (yellow_color[2] - paper_color[2]) * e_intensity)))
                    
                    hex_color = f"#{r:02x}{g:02x}{b:02x}"
                    style = f"bold #000000 on {hex_color} {base_style}"
                    
                # 3. 1D Gospels Style (including John 43)
                elif is_gospel_book and 'gospels' in word.stylometry_data:
                    gd = word.stylometry_data['gospels']
                    owner_id = gd.get('owner_id')
                    intensity = gd.get('intensity', 0)
                    
                    base_colors = {
                        40: (74, 144, 226), 41: (226, 74, 74), 42: (74, 226, 87), 43: (226, 200, 74)
                    }
                    
                    if owner_id in base_colors:
                        r2, g2, b2 = base_colors[owner_id]
                        r = int(paper_color[0] + (r2 - paper_color[0]) * intensity)
                        g = int(paper_color[1] + (g2 - paper_color[1]) * intensity)
                        b = int(paper_color[2] + (b2 - paper_color[2]) * intensity)
                        hex_color = f"#{r:02x}{g:02x}{b:02x}"
                        style = f"bold #000000 on {hex_color} {base_style}"
                        
                # 4. 1D Catholic Style (Hebrews, James, etc.)
                elif 'catholic' in word.stylometry_data and str(book_id) in word.stylometry_data['catholic']:
                    intensity = word.stylometry_data['catholic'][str(book_id)]
                    
                    # Same Blue used for other corpuses
                    blue_color = (74, 144, 226)
                    
                    r = int(paper_color[0] + (blue_color[0] - paper_color[0]) * intensity)
                    g = int(paper_color[1] + (blue_color[1] - paper_color[1]) * intensity)
                    b = int(paper_color[2] + (blue_color[2] - paper_color[2]) * intensity)
                    
                    hex_color = f"#{r:02x}{g:02x}{b:02x}"
                    style = f"bold #000000 on {hex_color} {base_style}"

            pass_stack.append(Text(greek_text, style=style))
            
            # Morph
            if DEFAULT_CONFIG.show_morphology:
                style = f"#66800b {base_style}" if not is_selected else "#66800b reverse"
                pass_stack.append(Text(word.morph, style=style))
            
            # Strongs
            if DEFAULT_CONFIG.show_strongs:
                 style = f"#24837b {base_style}" if not is_selected else "#24837b reverse"
                 pass_stack.append(Text(word.strongs or "", style=style))

            # Lemma
            if DEFAULT_CONFIG.show_lemma:
                 style = f"#66800b {base_style}" if not is_selected else "#66800b reverse"
                 pass_stack.append(Text((word.lemma or "").rstrip(), style=style))

            # Translation
            if DEFAULT_CONFIG.show_translation:
                 style = f"#bc5215 {base_style}" if not is_selected else "#bc5215 reverse"
                 pass_stack.append(Text(word.translation, style=style))

            stacks.append(pass_stack)

        PADDING = 2
        lines = []
        # ... (render logic remains same)
        current_line_stacks = []
        current_line_width = 0
        
        for stack in stacks:
            stack_width = max(len(t) for t in stack) if stack else 0
            
            if current_line_width + stack_width + PADDING > max_width and current_line_stacks:
                lines.append(self._render_line(current_line_stacks, PADDING))
                current_line_stacks = []
                current_line_width = 0
            
            current_line_stacks.append(stack)
            current_line_width += stack_width + PADDING
            
        if current_line_stacks:
            lines.append(self._render_line(current_line_stacks, PADDING))
            
        final_content = Text("\n").join(lines)
        translated_ref = translate_reference(self.current_verse_data.reference)
        self.update(Panel(final_content, title=f"[bold #ad8301]{translated_ref}[/]", border_style="#cecdc3"))

    def _render_line(self, line_stacks, padding):
        if not line_stacks:
            return Text("")
        
        max_rows = max(len(s) for s in line_stacks)
        combined_text = Text()
        
        for row_idx in range(max_rows):
            line_text = Text()
            for stack in line_stacks:
                item = stack[row_idx] if row_idx < len(stack) else Text("")
                stack_width = max(len(t) for t in stack)
                pad_len = stack_width - len(item)
                
                line_text.append(item)
                line_text.append(" " * (pad_len + padding))
            
            combined_text.append(line_text)
            combined_text.append("\n")
            
        return combined_text

# --- Main App ---

class OpenGNTApp(App):
    CSS = """
    Screen {
        layout: vertical;
        background: #f2f0e5;
        color: #100f0f;
    }
    
    Screen {
        layout: vertical;
        background: #f2f0e5;
        color: #100f0f;
        overflow-y: auto;
    }
    
    Header {
        height: 1;
        dock: top;
        background: #cecdc3;
        color: #100f0f;
    }

    InterlinearDisplay {
        height: auto;
        min-height: 5;
        border: solid #66800b;
        background: #f2f0e5;
    }
    
    InterlinearDisplay:focus {
        border: heavy #66800b;
    }

    #bottom-container {
        height: auto;
        border-top: solid #cecdc3;
    }

    #annotations-view {
        height: auto;
        border-bottom: solid #cecdc3;
        padding: 0 1;
    }

    #translations-view {
        height: auto;
        padding: 0 1;
    }
    
    .anno-pane {
        width: 50%;
        height: auto;
        border: solid #cecdc3;
        padding: 0 1; 
    }
    
    #verse-annotations {
        height: auto;
        padding: 0 1;
        border-top: solid #cecdc3;
    }

    #dictionary-view {
        height: auto;
        max-height: 15;
        border-top: solid #cecdc3;
        padding: 0 1;
        overflow-y: auto;
    }

    #parallels-view {
        height: auto;
        border-top: solid #cecdc3;
        padding: 0 1;
        background: #f2f0e5;
    }

    .parallel-link {
        color: #bc5215;
        text-style: bold underline;
        margin-right: 2;
    }

    .parallel-title {
        color: #ad8301;
        text-style: bold;
        margin-bottom: 1;
    }

    Toast {
        background: #100f0f;
        color: #f2f0e5;
        border: solid #ad8301;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", _("quit_app")),
        Binding("down", "next_verse", _("next_verse")),
        Binding("up", "prev_verse", _("prev_verse")),
        Binding("right", "next_word", _("next_word")),
        Binding("left", "prev_word", _("prev_word")),
        Binding("a", "edit_word_annotation", _("edit_word_ann")),
        Binding("A", "edit_lemma_annotation", _("edit_lemma_ann")),
        Binding("v", "edit_verse_annotation", _("edit_verse_ann")),
        Binding("V", "edit_verse_annotation", _("edit_verse_ann"), show=False),
        Binding("t", "edit_word_translation", _("edit_word_trans")),
        Binding("T", "edit_lemma_translation", _("edit_lemma_trans")),
        Binding("ctrl+e", "edit_greek_word", _("edit")),
        Binding("c", "show_concordance", _("show_concordance")),
        Binding("d", "show_dictionary", _("show_dictionary")),
        Binding("g", "goto_reference", _("go")),
        Binding("p", "focus_phrase", _("focus_phrase")),
        Binding("h", "show_help", _("show_help")),
        Binding("comma", "show_settings", _("show_settings")),
        Binding("s", "show_search", _("search")),
        Binding("b", "backup_database", _("backup_database")),
    ]

    selected_word_index = reactive(0)

    def __init__(self):
        super().__init__()
        self.state = OpenGNTState()
        self.TOOLTIP_DELAY = 0.1 # Make tooltips appear instantly

    def on_mount(self):
        self.load_verse()
        self.query_one(InterlinearDisplay).focus()

    def load_verse(self):
        self.state.load_verse()
        
        if self.state.current_verse_data:
            display = self.query_one(InterlinearDisplay)
            display.current_verse_data = self.state.current_verse_data
            
            # Reset selection if out of bounds (simplified logic)
            if self.selected_word_index >= len(self.state.current_verse_data.words):
                self.selected_word_index = 0
            
            display.selected_word_index = self.selected_word_index
            self.update_bottom_panels()
            self.update_phrase_panel()
            
    def update_phrase_panel(self):
        editor = self.query_one(PhraseEditor)
        if self.state.current_verse_data and self.state.current_verse_data.phrase_translations:
            # Assuming first translation is the one we want, like in tui.py
            editor.text = self.state.current_verse_data.phrase_translations[0].spanish_translation or ""
        else:
            editor.text = ""

    def update_bottom_panels(self):
        word = None
        # Update Annotations
        i_text = _("no_instance_ann")
        l_text = _("no_lemma_ann")
        
        if self.state.current_verse_data and self.state.current_verse_data.words and self.selected_word_index >= 0:
            if self.selected_word_index < len(self.state.current_verse_data.words):
                word = self.state.current_verse_data.words[self.selected_word_index]
                annos = self.state.anno_service.get_annotations_for_word_id(word.word_id)
                
                # Instance Content
                i_lines = []
                if annos['instance_annotations']:
                    for a in annos['instance_annotations']:
                        i_lines.append(f"{a.content}")
                if i_lines:
                    i_text = "\n".join(i_lines)
                
                # Lemma Content
                l_lines = []
                if annos['lemma_annotations']:
                    for a in annos['lemma_annotations']:
                        l_lines.append(f"{a.content}")
                if l_lines:
                    l_text = "\n".join(l_lines)

        v_text = _("no_verse_ann")
        if DEFAULT_CONFIG.show_verse_annotations:
            book = self.state.text_repo.get_book_by_name(self.state.book_name)
            if book:
                verse_annos = [a for a in self.state.anno_service.get_verse_annotations(
                    book.id, 
                    self.state.chapter, 
                    self.state.verse
                ) if a.annotation_type == 'verse']
                
                if verse_annos:
                    v_text = "\n".join([a.content for a in verse_annos])

        self.query_one("#instance-annotations", Static).update(Panel(i_text, title=_("instance_annotations_title"), border_style="none"))
        self.query_one("#lemma-annotations", Static).update(Panel(l_text, title=_("lemma_annotations_title"), border_style="none"))
        self.query_one("#verse-annotations", Static).update(Panel(v_text, title=_("verse_annotations_title"), border_style="none"))

        # Update Translations
        trans_text = ""
        if self.state.current_verse_data:
            lines = []
            if DEFAULT_CONFIG.show_spanish_translation and self.state.current_verse_data.spanish_verse_text:
                lines.append(f"[bold]{_('spanish_label')}:[/bold] {self.state.current_verse_data.spanish_verse_text}")
            if DEFAULT_CONFIG.show_latin_translation and self.state.current_verse_data.latin_verse_text:
                lines.append(f"[bold]{_('latin_label')}:[/bold] {self.state.current_verse_data.latin_verse_text}")
            if not lines:
                lines.append(_("trans_hidden"))
            trans_text = "\n".join(lines)
        
        self.query_one("#translations-view", Static).update(Panel(trans_text, title=_("translations_title"), border_style="none"))

        # Update Dictionary Panel
        dict_text = ""
        dict_view = self.query_one("#dictionary-view", Static)
        if DEFAULT_CONFIG.show_dictionary_panel:
            dict_view.display = True
            if self.state.current_verse_data and self.state.current_verse_data.words:
                word = self.state.current_verse_data.words[self.selected_word_index]
                definition = self.state.dict_service.get_definition(word.lemma)
                if definition:
                    dict_text = definition
                else:
                    dict_text = f"{_('no_def_found')} {word.lemma}"
            self.query_one("#dictionary-view", Static).update(Panel(dict_text, title=f"{_('dictionary_title')}: {word.lemma if word else ''}", border_style="none"))
        else:
            dict_view.display = False

        if self.state.current_verse_data and self.state.current_verse_data.parallel_pericopes:
            p_text = ""
            for p in self.state.current_verse_data.parallel_pericopes:
                p_text += f"[bold #ad8301]§ {p['title']}[/]\n"
                for book, ref in p["references"].items():
                    # Translate book name
                    t_book = translate_reference(book)
                    # Format ref for clicking: John 4:46b-54 -> John 4:46
                    # We'll take the first part of the range
                    nav_ref = f"{book} {ref.split('-')[0].strip()}"
                    p_text += f"[@click=\"app.goto_ref('{nav_ref}')\"][bold underline #bc5215]{t_book} {ref}[/][/]  "
                p_text += "\n\n"
            
            if not p_text:
                p_text = _("no_parallels")
        else:
            p_text = _("no_parallels")

        self.query_one("#parallels-view", Static).update(Panel(p_text, title=_("parallels_title"), border_style="none"))

    def action_show_settings(self) -> None:
        """Show the settings modal."""
        self.push_screen(SettingsScreen())

    def action_refresh_view(self) -> None:
        """Refresh the entire view based on current settings."""
        self.load_verse()
        self.query_one(BottomMenuBar).update()
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield PhrasePanel()
        yield InterlinearDisplay()
        with Vertical(id="bottom-container"):
            with Horizontal(id="annotations-view"):
                yield Static(id="instance-annotations", classes="anno-pane")
                yield Static(id="lemma-annotations", classes="anno-pane")
            yield Static(id="translations-view")
            yield Static(id="verse-annotations")
            yield Static(id="parallels-view")
            yield Static(id="dictionary-view")
        yield BottomMenuBar()

    def action_next_verse(self):
        self.state.next_verse()
        self.selected_word_index = 0
        self.load_verse()
        
    def action_prev_verse(self):
        self.state.prev_verse()
        self.selected_word_index = 0
        self.load_verse()

    def action_next_word(self):
        if self.state.current_verse_data and self.state.current_verse_data.words:
            if self.selected_word_index < len(self.state.current_verse_data.words) - 1:
                self.selected_word_index += 1
                self.query_one(InterlinearDisplay).selected_word_index = self.selected_word_index
                self.update_bottom_panels()

    def action_prev_word(self):
        if self.state.current_verse_data and self.state.current_verse_data.words:
            if self.selected_word_index > 0:
                self.selected_word_index -= 1
                self.query_one(InterlinearDisplay).selected_word_index = self.selected_word_index
                self.update_bottom_panels()

    async def action_edit_word_annotation(self):
        """Edit annotations for the selected word instance using a modal."""
        if not self.state.current_verse_data or not self.state.current_verse_data.words:
            return
            
        word_idx = self.selected_word_index
        if word_idx >= len(self.state.current_verse_data.words):
            return

        word = self.state.current_verse_data.words[word_idx]
        
        # Fetch current text
        annos = self.state.anno_service.get_annotations_for_word_id(word.word_id)
        existing_list = annos['instance_annotations']
        initial_text = "\n\n".join([a.content for a in existing_list])
        
        def save_handler(result: Optional[str]):
            if result is not None:
                self.state.anno_service.set_word_annotation(word.word_id, result)
                # Refresh
                self.update_bottom_panels()
                self.query_one(InterlinearDisplay).focus()

        self.push_screen(AnnotationEditorScreen(f"Edit Instance Annotation: {word.text}", initial_text), save_handler)

    async def action_edit_lemma_annotation(self):
        """Edit annotations for the selected word's lemma using a modal."""
        if not self.state.current_verse_data or not self.state.current_verse_data.words:
            return
            
        word_idx = self.selected_word_index
        if word_idx >= len(self.state.current_verse_data.words):
            return

        word = self.state.current_verse_data.words[word_idx]
        
        # Fetch current text
        annos = self.state.anno_service.get_annotations_for_word_id(word.word_id)
        existing_list = annos['lemma_annotations']
        initial_text = "\n\n".join([a.content for a in existing_list])
        
        def save_handler(result: Optional[str]):
            if result is not None:
                self.state.anno_service.set_lemma_annotation(word.lemma, result)
                # Refresh
                self.update_bottom_panels()
                self.query_one(InterlinearDisplay).focus()

        self.push_screen(AnnotationEditorScreen(f"Edit Lemma Annotation: {word.lemma}", initial_text), save_handler)

    async def action_edit_verse_annotation(self):
        """Edit annotations for the current verse using a modal."""
        if not self.state.current_verse_data:
            return
            
        # Get book_id
        book = self.state.text_repo.get_book_by_name(self.state.book_name)
        if not book:
            return

        # Fetch current text
        verse_annos = [a for a in self.state.anno_service.get_verse_annotations(
            book.id, 
            self.state.chapter, 
            self.state.verse
        ) if a.annotation_type == 'verse']
        
        initial_text = "\n\n".join([a.content for a in verse_annos])
        
        def save_handler(result: Optional[str]):
            if result is not None:
                self.state.anno_service.set_verse_annotation(book.id, self.state.chapter, self.state.verse, result)
                # Refresh
                self.update_bottom_panels()
                self.query_one(InterlinearDisplay).focus()

        self.push_screen(AnnotationEditorScreen(f"Edit Verse Annotation: {self.state.current_verse_data.reference}", initial_text), save_handler)

    async def action_goto_reference(self, initial_ref: Optional[str] = None):
        """Handle goto reference."""
        def handle_goto(result: Optional[str]):
            if not result:
                return
                
            book_id, chapter, verse = parse_reference(result)
            if book_id is None:
                # Try fallback: maybe it's just a book name?
                from opengnt_interface.bible_books import find_book_id
                
                # Check for relative navigation (e.g. "4:3" or "4,3")
                import re
                rel_match = re.match(r'^\s*(\d+)[:,\s]+(\d+)\s*$', result)
                if rel_match:
                    # Use current book
                    chapter = int(rel_match.group(1))
                    verse = int(rel_match.group(2))
                    # effective book is current book
                    current_book = self.state.text_repo.get_book_by_name(self.state.book_name)
                    if current_book:
                        book_id = current_book.id
                    else:
                        return # Should not happen if state is valid
                else:
                    # Fallback: maybe it's just a book name?
                    book_id = find_book_id(result.strip())
                    if book_id:
                        chapter = 1
                        verse = 1
                    else:
                        return # Invalid

            # Check if book exists in DB
            book = self.state.text_repo.get_book(book_id)
            if not book:
                return
                
            self.state.book_name = book.name
            self.state.chapter = chapter
            self.state.verse = verse
            self.selected_word_index = 0
            self.load_verse()
            self.query_one(InterlinearDisplay).focus()

        self.push_screen(GoToScreen(), handle_goto)

    async def action_edit_word_translation(self):
        """Edit translation for selection word instance."""
        if not self.state.current_verse_data or not self.state.current_verse_data.words:
            return

        word_idx = self.selected_word_index
        if word_idx >= len(self.state.current_verse_data.words):
            return

        word = self.state.current_verse_data.words[word_idx]
        
        # Prepare context
        morph_code = word.morph
        morph_expanded = expand_morphology(morph_code) if morph_code else ""
        morph_display = f"{morph_code} ({morph_expanded})" if morph_expanded else morph_code
        
        current_val = word.translation
        
        def save_handler(result: Optional[str]):
            if result is not None:
                self.state.trans_service.set_word_translation(word.word_id, result)
                self.load_verse()
                self.query_one(InterlinearDisplay).focus()

        self.push_screen(
            TranslationEditorScreen(f"Edit Word Translation: {word.text}", morph_display, current_val), 
            save_handler
        )

    async def action_edit_lemma_translation(self):
        """Edit translation for selected word lemma."""
        if not self.state.current_verse_data or not self.state.current_verse_data.words:
            return

        word_idx = self.selected_word_index
        if word_idx >= len(self.state.current_verse_data.words):
            return

        word = self.state.current_verse_data.words[word_idx]
        
        # Prepare context
        morph_code = word.morph
        morph_expanded = expand_morphology(morph_code) if morph_code else ""
        morph_display = f"{morph_code} ({morph_expanded})" if morph_expanded else morph_code
        
        current_val = self.state.trans_service.get_lemma_translation_text(word.lemma)
        
        def save_handler(result: Optional[str]):
            if result is not None:
                self.state.trans_service.set_lemma_translation(word.lemma, result)
                self.load_verse()
                self.query_one(InterlinearDisplay).focus()

        self.push_screen(
            TranslationEditorScreen(f"Edit Lemma Translation: {word.lemma}", morph_display, current_val), 
            save_handler
        )

    def _remove_accents(self, input_str):
        if not input_str:
            return ""
        nfkd_form = unicodedata.normalize('NFKD', input_str)
        return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

    async def action_edit_greek_word(self):
        """Open the GNT Editing Tools menu."""
        if not self.state.current_verse_data or not self.state.current_verse_data.words:
            return

        word_idx = self.selected_word_index
        if word_idx >= len(self.state.current_verse_data.words):
            return

        word = self.state.current_verse_data.words[word_idx]

        def menu_handler(choice: Optional[str]):
            if not choice:
                self.query_one(InterlinearDisplay).focus()
                return

            if choice == "edit_info":
                self._do_edit_word_info(word.word_id)
            elif choice == "move_left":
                self._do_move_word(word.word_id, -1)
            elif choice == "move_right":
                self._do_move_word(word.word_id, 1)
            elif choice == "add_before":
                self._do_add_word(word_idx)
            elif choice == "add_after":
                self._do_add_word(word_idx + 1)
            elif choice == "remove_word":
                self._do_remove_word(word.word_id)
            elif choice == "edit_punct":
                self._do_edit_punctuation(word.word_id)

        self.push_screen(GreekToolsMenu(word.text), menu_handler)

    def _do_edit_word_info(self, word_id: int):
        # Fetch fresh data from repo
        db_word = self.state.text_repo.get_word(word_id)
        if not db_word: return
            
        word_data = {
            'greek_accented': db_word.greek_accented,
            'lexeme': db_word.lexeme,
            'rmac': db_word.rmac,
            'strongs': db_word.strongs
        }
        
        def save_handler(result: Optional[dict]):
            if result:
                unaccented = self._remove_accents(result['greek_accented'])
                if self.state.text_repo.update_word(word_id, result['greek_accented'], unaccented, result['lexeme'], result['rmac'], result['strongs']):
                    self.load_verse()
                    self.notify("Word updated")
            self.query_one(InterlinearDisplay).focus()

        self.push_screen(GreekWordEditorScreen(f"Edit Word Info", word_data), save_handler)

    def _do_move_word(self, word_id: int, direction: int):
        if self.state.text_repo.move_word(word_id, direction):
            # Update selection to keep focus on the moved word
            self.selected_word_index += direction
            self.load_verse()
            self.notify("Word moved")
        else:
            self.notify("Cannot move word in that direction", severity="warning")
        self.query_one(InterlinearDisplay).focus()

    def _do_remove_word(self, word_id: int):
        # Could add a confirmation here, but let's go direct for now or use a simple alert
        if self.state.text_repo.delete_word(word_id):
            self.load_verse()
            self.notify("Word removed")
        else:
            self.notify("Failed to remove word", severity="error")
        self.query_one(InterlinearDisplay).focus()

    def _do_add_word(self, target_order_idx: int):
        # target_order_idx is 0-based index in the current verse words list
        # DB word_order is 1-based.
        target_order = target_order_idx + 1
        
        word_data = {
            'greek_accented': '',
            'lexeme': '',
            'rmac': '',
            'strongs': ''
        }
        
        def save_handler(result: Optional[dict]):
            if result:
                book = self.state.text_repo.get_book_by_name(self.state.book_name)
                unaccented = self._remove_accents(result['greek_accented'])
                result['greek_unaccented'] = unaccented
                if self.state.text_repo.insert_word(book.id, self.state.chapter, self.state.verse, target_order, result):
                    # Select the new word
                    self.selected_word_index = target_order_idx
                    self.load_verse()
                    self.notify("Word inserted")
            self.query_one(InterlinearDisplay).focus()

        self.push_screen(GreekWordEditorScreen(f"Add New Greek Word", word_data), save_handler)

    def _do_edit_punctuation(self, word_id: int):
        db_word = self.state.text_repo.get_word(word_id)
        if not db_word: return

        # Strip tags and whitespace for display
        def strip_pm(s):
            if not s: return ""
            return s.replace("<pm>", "").replace("</pm>", "").strip()

        def wrap_pm(s):
            if not s: return ""
            # Only wrap if contains actual punctuation
            if not s.strip(): return ""
            return f"<pm>{s}</pm>"

        def save_handler(result: Optional[dict]):
            if result:
                # Re-add tags for storage, stripping accidental whitespace
                p_before = wrap_pm(result['before'].strip())
                p_after = wrap_pm(result['after'].strip())
                if self.state.text_repo.update_punctuation(word_id, p_before, p_after):
                    self.load_verse()
            self.query_one(InterlinearDisplay).focus()

        self.push_screen(PunctuationEditorScreen("Edit Punctuation", strip_pm(db_word.punct_before), strip_pm(db_word.punct_after)), save_handler)

    def action_focus_phrase(self):
        """Focus the phrase editor."""
        self.query_one(PhraseEditor).focus()
        
    def action_save_phrase_translation(self):
        """Save the phrase translation from the editor."""
        if not self.state.current_verse_data:
            return
            
        new_text = self.query_one(PhraseEditor).text
        book = self.state.text_repo.get_book_by_name(self.state.book_name)
        if book:
            self.state.trans_service.set_phrase_translation(book.id, self.state.chapter, self.state.verse, new_text)
            self.load_verse() # Reload to confirm/refresh
            
        self.query_one(InterlinearDisplay).focus()
        
    def action_cancel_phrase_edit(self):
        """Cancel phrase editing and revert text."""
        self.update_phrase_panel() # Revert to current state
        self.query_one(InterlinearDisplay).focus()

    async def action_show_concordance(self):
        """Show concordance for current lemma."""
        if not self.state.current_verse_data or not self.state.current_verse_data.words:
            return
            
        word_idx = self.selected_word_index
        if word_idx >= len(self.state.current_verse_data.words):
            return

        word = self.state.current_verse_data.words[word_idx]
        lemma = word.lemma
        
        data = self.state.interlinear_service.get_concordance_data(lemma)
        self.push_screen(ConcordanceScreen(data))

    async def action_show_dictionary(self):
        """Show dictionary entry for current lemma."""
        if not self.state.current_verse_data or not self.state.current_verse_data.words:
            return
            
        word_idx = self.selected_word_index
        if word_idx >= len(self.state.current_verse_data.words):
            return

        word = self.state.current_verse_data.words[word_idx]
        lemma = word.lemma
        
        definition = self.state.dict_service.get_definition(lemma)
        if definition:
            self.push_screen(DictionaryScreen(lemma, definition))
        else:
            self.notify(f"No definition found for {lemma}", severity="warning")

    async def action_backup_database(self):
        """Create a database backup."""
        try:
            # Create backup directory
            backup_dir = backups_directory()
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            backup_filename = f"opengnt_backup_{timestamp}.db"
            backup_path = backup_dir / backup_filename
            shutil.copy2(database_path(), backup_path)
            
            # Get file size
            size_mb = backup_path.stat().st_size / 1024 / 1024
            
            self.notify(
                _("backup_success").format(path=backup_path.name, size=f"{size_mb:.2f} MB"),
                title=_("backup_successful_title"),
                timeout=5
            )
        except Exception as e:
            self.notify(
                title="Backup Failed",
                severity="error",
                timeout=5
            )

    async def action_goto_ref(self, ref: str):
        """Action triggered by clicking a parallel link."""
        from opengnt_interface.bible_books import parse_reference
        book_id, chapter, verse = parse_reference(ref)
        if book_id is not None:
            book = self.state.text_repo.get_book(book_id)
            if book:
                self.state.book_name = book.name
                self.state.chapter = chapter
                self.state.verse = verse
                self.selected_word_index = 0
                self.load_verse()
                self.query_one(InterlinearDisplay).focus()
                self.notify(f"Navigated to {ref}")

    async def action_goto_ref_and_close(self, ref: str) -> None:
        """Go to a specific reference and close the current screen."""
        await self.action_goto_ref(ref)
        self.pop_screen()

    def action_show_search(self):
        """Show the search modal."""
        self.push_screen(SearchScreen())

    def action_show_help(self):
        """Show the help modal."""
        self.push_screen(HelpScreen())


def main() -> None:
    """Entry point for the console script and ``python -m`` invocation."""
    if not database_path().is_file():
        Console().print(
            "[red]No local database is installed.[/red] Run "
            "[bold]opengnt setup --full-install[/bold] (or "
            "[bold]uv run opengnt setup --full-install[/bold] from a checkout) to build one "
            "from the bundled startup data."
        )
        raise SystemExit(1)
    OpenGNTApp().run()


if __name__ == "__main__":
    main()
