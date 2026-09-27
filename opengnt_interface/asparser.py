from bs4 import BeautifulSoup, NavigableString
from rich.text import Text

class AbbottSmithParser:
    def __init__(self):
        # Flexoki-inspired color palette
        self.colors = {
            "headword": "#bc5215", # Orange
            "morph": "#66800b",    # Green
            "strongs": "#24837b",  # Cyan
            "ref": "#24837b",      # Cyan
            "heb": "#66800b",      # Green
            "lat": "#4385be",      # Blue
            "label": "#ad8301",    # Yellow
            "para": "#100f0f"       # Ink
        }

    def format_entry(self, html_content):
        """Converts raw Abbott-Smith HTML/XML to a Rich Text object."""
        if not html_content:
            return Text("No content available.")

        soup = BeautifulSoup(html_content, "html.parser")
        rich_text = Text()

        # Handle root <entry>
        entry = soup.find("entry")
        if entry:
            # 1. Header Logic (Strong's + Headword)
            header_text = Text()
            # Logeion type is often occurrencesNT (case-sensitive in some BS versions)
            note = entry.find("note", type=lambda t: t and t.lower() == "occurrencesnt")
            if note:
                note_text = note.get_text()
                if "Strong" in note_text:
                    parts = note_text.split("Strong")
                    strong_num = parts[-1].strip()
                    header_text.append(f"Strong G{strong_num} ", style=f"italic {self.colors['strongs']}")
                note.decompose()

            orth = entry.find("orth")
            if orth:
                if header_text: header_text.append("| ")
                header_text.append(orth.get_text(), style=f"bold {self.colors['headword']}")
                orth.decompose()
            
            rich_text.append(header_text)

            # 2. Skip leading fluff (BRs and whitespace)
            # Re-fetch children after decomposing
            children = list(entry.children)
            start_idx = 0
            while start_idx < len(children):
                child = children[start_idx]
                if isinstance(child, NavigableString) and not child.strip():
                    start_idx += 1
                elif getattr(child, 'name', None) == "br":
                    start_idx += 1
                else:
                    break
            
            # 3. Process the remaining body
            for i in range(start_idx, len(children)):
                self._process_node(children[i], rich_text)
        else:
            self._process_node(soup, rich_text)

        # Final cleanup
        rich_text.rstrip()
        return rich_text

    def _process_node(self, node, rich_text, indent=0):
        """Recursively processes HTML nodes and maps them to Rich styles."""
        if isinstance(node, NavigableString):
            text = str(node)
            if not text.strip() and text != " ": return
            
            # If we are starting a new line, strip leading space from text
            if rich_text and str(rich_text)[-1] == "\n":
                text = text.lstrip()
            
            # Avoid double spaces
            if text == " " and rich_text and str(rich_text)[-1] == " ":
                return
            rich_text.append(text)
            return

        if node.name in ["entry", "orth", "note", "pb"]:
            return

        for child in node.children:
            if isinstance(child, NavigableString):
                self._process_node(child, rich_text, indent)
            elif child.name == "p":
                style_attr = child.get("style", "")
                margin = 0
                if "margin-left: 40px" in style_attr: margin = 4
                elif "margin-left: 80px" in style_attr: margin = 8
                elif "margin-left: 120px" in style_attr: margin = 12
                
                if rich_text and str(rich_text)[-1] != "\n":
                    rich_text.append("\n")
                rich_text.append(" " * margin)
                self._process_node(child, rich_text, indent=margin)
            elif child.name == "b":
                style = "bold"
                if child.find("i"): style += " italic"
                rich_text.append(child.get_text(), style=style)
            elif child.name == "i":
                rich_text.append(child.get_text(), style="italic")
            elif child.name == "ref":
                rich_text.append(child.get_text(), style=f"underline {self.colors['ref']}")
            elif child.name == "foreign":
                lang = child.get("xml:lang", "")
                color = self.colors.get(lang, "italic")
                rich_text.append(child.get_text(), style=color)
            elif child.name == "br":
                if rich_text and str(rich_text)[-1] != "\n":
                    rich_text.append("\n" + " " * indent)
            elif child.name == "etym":
                self._inline_container(child, rich_text, "Etym")
            elif child.name == "seg":
                if child.get("type") == "septuagint":
                    self._inline_container(child, rich_text, "LXX")
                else:
                    self._process_node(child, rich_text, indent)
            elif child.name in ["entry", "orth", "note", "pb"]:
                pass
            else:
                self._process_node(child, rich_text, indent)

    def _inline_container(self, node, rich_text, label):
        """Helper for Etym and LXX. Attempts to merge with existing brackets."""
        if rich_text and str(rich_text)[-1] not in ["\n", " "]:
            rich_text.append(" ")
            
        rich_text.append(f"[{label}: ", style=f"bold {self.colors['label']}")
        
        # Process children but remove leading/trailing brackets from strings
        for child in node.children:
            if isinstance(child, NavigableString):
                text = str(child)
                if text.strip() == "[" or text.strip() == "]": continue
                # More nuanced trim
                if text.startswith("["): text = text[1:]
                if text.endswith("]"): text = text[:-1]
                rich_text.append(text)
            else:
                self._process_node(child, rich_text)
                
        rich_text.append("]", style=f"bold {self.colors['label']}")
