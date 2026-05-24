import json
import subprocess
import sys


def _run(args, env=None):
    return subprocess.run(
        [sys.executable, "-m", "juvera_sdk.cli", *args],
        capture_output=True, text=True, env=env,
    )


def test_demo_default_writes_ndjson_and_prints_card(tmp_path):
    env = {"HOME": str(tmp_path), "PATH": __import__("os").environ.get("PATH", ""),
           "NO_COLOR": "1"}
    r = _run(["demo", "--seed", "1"], env=env)
    assert r.returncode == 0, r.stderr
    assert "Juvera captured 1 agent run" in r.stdout
    assert "ticket_deflection" in r.stdout
    files = list((tmp_path / ".juvera" / "captures").rglob("demo-*.ndjson"))
    assert len(files) == 1
    line = files[0].read_text().strip().splitlines()[0]
    event = json.loads(line)
    assert event["source"] == "demo"
    assert event["workflow_type"] == "ticket_deflection"
    # Cost must come from catalog (catches hardcoded-number drift)
    assert 0.00015 < event["agent_cost_usd"] < 0.00020
    # _user_message must NOT be persisted (it's a private/card-only field)
    assert "_user_message" not in event
    # captured_at must be overridden from the placeholder, not "1970-..."
    assert not event["captured_at"].startswith("1970-")


def test_demo_no_save_skips_ndjson(tmp_path):
    env = {"HOME": str(tmp_path), "PATH": __import__("os").environ.get("PATH", ""),
           "NO_COLOR": "1"}
    r = _run(["demo", "--no-save", "--seed", "1"], env=env)
    assert r.returncode == 0
    assert "Juvera captured 1 agent run" in r.stdout
    assert not (tmp_path / ".juvera" / "captures").exists()


def test_demo_workflow_flag(tmp_path):
    env = {"HOME": str(tmp_path), "PATH": __import__("os").environ.get("PATH", ""),
           "NO_COLOR": "1"}
    r = _run(["demo", "--workflow", "lead_qualification", "--seed", "1"], env=env)
    assert r.returncode == 0
    assert "lead_qualification" in r.stdout


def test_demo_renders_card_when_save_fails(tmp_path):
    """If local write fails, demo still prints the card (warning to stderr)."""
    # Make HOME a path that exists as a FILE, not a dir — write attempts will fail.
    bad_home = tmp_path / "not_a_dir"
    bad_home.write_text("blocking file")
    env = {"HOME": str(bad_home), "PATH": __import__("os").environ.get("PATH", ""),
           "NO_COLOR": "1"}
    r = _run(["demo", "--seed", "1"], env=env)
    assert r.returncode == 0, r.stderr
    assert "Juvera captured 1 agent run" in r.stdout
    assert "could not save capture" in r.stderr
