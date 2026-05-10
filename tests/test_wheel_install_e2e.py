"""Build → install in tmp venv → verify CLI commands work end-to-end."""
import os
import subprocess
import sys
import venv
from pathlib import Path

import pytest


@pytest.mark.slow
def test_wheel_install_demo_and_report(tmp_path):
    """Build wheel, install in isolated venv, run demo and report CLI end-to-end."""
    sdk_dir = Path(__file__).resolve().parent.parent
    dist = tmp_path / "dist"
    dist.mkdir()
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist)],
        cwd=str(sdk_dir),
        check=True,
        capture_output=True,
    )
    wheel = next(dist.glob("juvera_sdk-*.whl"))

    venv_dir = tmp_path / "venv"
    venv.EnvBuilder(with_pip=True).create(str(venv_dir))
    py = venv_dir / "bin" / "python"
    juvera = venv_dir / "bin" / "juvera"

    subprocess.run(
        [str(py), "-m", "pip", "install", str(wheel)],
        check=True,
        capture_output=True,
    )

    home = tmp_path / "home"
    home.mkdir()
    env = {
        "HOME": str(home),
        "PATH": os.environ.get("PATH", ""),
        "NO_COLOR": "1",
    }

    # Step 1: juvera demo
    r = subprocess.run(
        [str(juvera), "demo", "--seed", "1"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, f"demo failed: {r.stderr}"
    assert "Juvera captured 1 agent run" in r.stdout

    # Step 2: juvera report
    r = subprocess.run(
        [str(juvera), "report", "--no-open"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, f"report failed: {r.stderr}"
    assert "Report written to" in r.stdout

    # Step 3: catalog packaging (FROM THE INSTALLED WHEEL, not the editable dev tree)
    r = subprocess.run(
        [
            str(py),
            "-c",
            "from juvera_sdk.costs import compute_token_cost_usd; "
            "v = compute_token_cost_usd('gpt-4o-mini', 421, 187, 'openai'); "
            "assert 0.00015 < v < 0.00020, v",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, f"catalog lookup failed from installed wheel: {r.stderr}"
