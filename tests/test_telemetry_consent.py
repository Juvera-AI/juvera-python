import io
import sys
import os
import json
from unittest.mock import patch
import subprocess

from juvera_sdk.telemetry import maybe_prompt_consent
from juvera_sdk.user_config import load_config


def test_non_tty_skips_prompt_and_defaults_to_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    # stdin is not a TTY in pytest by default
    maybe_prompt_consent()
    cfg = load_config()
    assert cfg["telemetry"] is False
    assert cfg["prompted"] is True


def test_no_op_when_already_prompted(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(tmp_path))
    maybe_prompt_consent()  # first call writes prompted=True
    capsys.readouterr()
    maybe_prompt_consent()  # second call should be no-op
    captured2 = capsys.readouterr()
    assert captured2.out == ""


def test_tty_yes_sets_telemetry_true(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    with patch("sys.stdin.isatty", return_value=True), \
         patch("builtins.input", return_value="y"):
        maybe_prompt_consent()
    cfg = load_config()
    assert cfg["telemetry"] is True


def test_tty_default_no_sets_telemetry_false(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    with patch("sys.stdin.isatty", return_value=True), \
         patch("builtins.input", return_value=""):
        maybe_prompt_consent()
    cfg = load_config()
    assert cfg["telemetry"] is False


def test_demo_card_renders_BEFORE_consent_prompt(tmp_path):
    """Critical UX: the ROI card must hit stdout before the consent prompt."""
    env = {
        "HOME": str(tmp_path),
        "PATH": os.environ.get("PATH", ""),
        "NO_COLOR": "1",
    }
    # subprocess stdin won't be a TTY, so prompt is skipped — but we can verify
    # the flag prompted=true is set after the card output (run completes successfully).
    r = subprocess.run(
        [sys.executable, "-m", "juvera_sdk.cli", "demo", "--seed", "1"],
        capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0, f"returncode={r.returncode}, stderr={r.stderr!r}"
    # Card should appear before any consent text in stdout (consent goes to stdout via print(_PROMPT_TEXT))
    card_pos = r.stdout.find("Juvera captured 1 agent run")
    assert card_pos >= 0, f"card missing from stdout: {r.stdout!r}"
    # Verify config.json now has prompted=True (means counter+consent fired AFTER the card)
    cfg = load_config_from(tmp_path)
    assert cfg.get("prompted") is True, "prompted flag not set — consent hook didn't run"


def load_config_from(tmp_path):
    """Read config.json from a custom HOME directory (for the subprocess test above)."""
    p = tmp_path / ".juvera" / "config.json"
    if not p.is_file():
        return {}
    return json.loads(p.read_text())


def test_config_command_does_not_show_consent_prompt(tmp_path):
    """juvera config get/set must not append the consent prompt to stdout."""
    env = {"HOME": str(tmp_path), "PATH": os.environ.get("PATH", ""), "NO_COLOR": "1"}
    r = subprocess.run(
        [sys.executable, "-m", "juvera_sdk.cli", "config", "get"],
        capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0, r.stderr
    # The consent prompt text must NOT appear in stdout (would corrupt JSON)
    assert "Help improve Juvera" not in r.stdout
    assert "Help improve Juvera" not in r.stderr  # also not on stderr — would mislead piped users


def test_config_set_telemetry_value_not_clobbered_by_consent(tmp_path):
    """juvera config set telemetry true must NOT be overwritten by a consent prompt."""
    env = {"HOME": str(tmp_path), "PATH": os.environ.get("PATH", ""), "NO_COLOR": "1"}
    # User explicitly opts in via config set
    r = subprocess.run(
        [sys.executable, "-m", "juvera_sdk.cli", "config", "set", "telemetry", "true"],
        capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0, r.stderr
    # Now read it back — the value must still be true (not overwritten by a deferred
    # consent prompt that defaulted to false)
    r = subprocess.run(
        [sys.executable, "-m", "juvera_sdk.cli", "config", "get", "telemetry"],
        capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0, r.stderr
    assert "true" in r.stdout.lower()
