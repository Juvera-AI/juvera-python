import subprocess
import sys
import os
from pathlib import Path


def _run(args, env=None):
    return subprocess.run(
        [sys.executable, "-m", "juvera_sdk.cli", *args],
        capture_output=True, text=True, env=env,
    )


def _extract_report_path(stdout: str) -> Path:
    """CLI prints 'Report written to /path/to/file'. Extract the path."""
    for line in stdout.strip().splitlines():
        if line.startswith("Report written to "):
            return Path(line[len("Report written to "):].strip())
    raise AssertionError(f"No 'Report written to' line in stdout: {stdout!r}")


def test_report_empty_state(tmp_path):
    env = {"HOME": str(tmp_path), "PATH": os.environ.get("PATH", ""), "NO_COLOR": "1"}
    r = _run(["report", "--no-open"], env=env)
    assert r.returncode == 0, r.stderr
    out_path = _extract_report_path(r.stdout)
    html = out_path.read_text()
    assert "0 agent runs" in html


def test_report_after_demo_renders_html(tmp_path):
    env = {"HOME": str(tmp_path), "PATH": os.environ.get("PATH", ""), "NO_COLOR": "1"}
    _run(["demo", "--seed", "1"], env=env)
    r = _run(["report", "--no-open"], env=env)
    assert r.returncode == 0, r.stderr
    out_path = _extract_report_path(r.stdout)
    html = out_path.read_text()
    assert "Juvera ROI Report" in html
    assert "ticket_deflection" in html


