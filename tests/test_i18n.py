import sys
from pathlib import Path

# Add project root to sys.path
root = Path(__file__).parent.parent
sys.path.append(str(root))

from opengnt_interface.i18n import _, set_language, manager

def test_i18n():
    print("Testing i18n system...")
    
    # Test English (default)
    set_language("en")
    assert _("app_title") == "OpenGNT - Multi-Language Greek New Testament"
    assert _("save") == "Save"
    print("✓ English translations loaded correctly.")
    
    # Test Spanish
    set_language("es")
    assert _("app_title") == "OpenGNT - Nuevo Testamento Griego Multilingüe"
    assert _("save") == "Guardar"
    print("✓ Spanish translations loaded correctly.")
    
    # Test Fallback
    set_language("es")
    # Add a dummy key to en.json only for testing if you want, 
    # but here we just check if it returns key if not found in both
    assert _("non_existent_key") == "non_existent_key"
    print("✓ Fallback (key as default) works.")
    
    # Test formatting
    set_language("en")
    res = _("error_book_not_found").format(book="Genesis")
    assert res == "Error: Book Genesis not found"
    print("✓ String formatting works.")

if __name__ == "__main__":
    try:
        test_i18n()
        print("\nAll i18n tests passed!")
    except AssertionError as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        sys.exit(1)
