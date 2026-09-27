"""Locations for mutable, user-installed OpenGNT resources.

The repository and installed package are read-only application code.  Databases,
settings, and locally supplied resources therefore live in a user-data directory.
Set ``OPENGNT_DATA_DIR`` to use a different directory (particularly useful for
tests and portable installations).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIRECTORY_NAME = "opengnt-interface"


def data_directory() -> Path:
    """Return the application-data directory without creating it."""
    override = os.environ.get("OPENGNT_DATA_DIR")
    if override:
        return Path(override).expanduser()

    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / APP_DIRECTORY_NAME


def database_path() -> Path:
    return data_directory() / "opengnt.db"


def settings_path() -> Path:
    return data_directory() / "settings.json"


def dictionary_path() -> Path:
    return data_directory() / "abbotsmith" / "dictionary.json"


def backups_directory() -> Path:
    return data_directory() / "backups"
