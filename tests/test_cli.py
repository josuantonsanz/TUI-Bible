import subprocess
import sys
from pathlib import Path

import pytest
import typer

ROOT = Path(__file__).parent.parent
sys.path.append(str(ROOT))

from opengnt_interface import cli

CLI_TARGET = [sys.executable, "-m", "opengnt_interface.cli"]


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        CLI_TARGET + list(arguments), cwd=ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False
    )


def test_cli_help_lists_setup_command():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "OpenGNT Interface CLI" in result.stdout
    assert "setup" in result.stdout


def test_setup_help_documents_local_rights_acknowledgement():
    result = run_cli("setup", "--help")
    assert result.returncode == 0
    # Rich wraps long options to the current terminal width.
    assert "acknowledge-local" in result.stdout


def test_setup_help_documents_full_install():
    result = run_cli("setup", "--help")
    assert result.returncode == 0
    assert "full-install" in result.stdout


def test_default_input_dir_points_to_bundled_startup():
    assert cli._default_input_dir() == ROOT / "startup"


def test_optional_resource_rights_confirmation_accepts_yes(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(cli.typer, "confirm", lambda prompt, default: calls.append((prompt, default)) or True)

    cli._confirm_optional_resource("dictionary", tmp_path / "abbotsmith.json")

    assert len(calls) == 1
    assert calls[0][1] is False
    assert "dictionary" in calls[0][0]


def test_optional_resource_rights_confirmation_rejects_no(monkeypatch, tmp_path):
    monkeypatch.setattr(cli.typer, "confirm", lambda prompt, default: False)

    with pytest.raises(typer.Exit) as error:
        cli._confirm_optional_resource("bj", tmp_path / "spanish_bible.json")

    assert error.value.exit_code == 2


def test_read_without_an_installed_database_fails_cleanly(tmp_path):
    result = subprocess.run(
        CLI_TARGET + ["read", "John 1:1"],
        cwd=ROOT,
        env={**__import__("os").environ, "OPENGNT_DATA_DIR": str(tmp_path)},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert result.returncode == 1
    assert "Database not found" in result.stdout
