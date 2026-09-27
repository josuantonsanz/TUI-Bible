import subprocess
import sys
from pathlib import Path

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


def test_setup_help_documents_bj_option():
    result = run_cli("setup", "--help")
    assert result.returncode == 0
    # Rich wraps long options to the current terminal width.
    assert "include-bj" in result.stdout
    assert "bibliaEsp.pk" in result.stdout


def test_setup_help_documents_full_install():
    result = run_cli("setup", "--help")
    assert result.returncode == 0
    assert "full-install" in result.stdout


def test_setup_help_documents_na28_option():
    result = run_cli("setup", "--help")
    assert result.returncode == 0
    assert "include-na28" in result.stdout


def test_default_input_dir_points_to_bundled_startup():
    assert cli._default_input_dir() == ROOT / "startup"


def test_bundled_bj_pickle_is_available():
    assert (ROOT / "startup" / "bibliaEsp.pk").is_file()


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
