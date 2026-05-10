"""Build the wheel and verify required data files are inside."""
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest


@pytest.mark.slow
def test_wheel_includes_template_and_pricing_catalog(tmp_path):
    """Verify wheel contains templates/*.j2 and data/*.json files."""
    sdk_dir = Path(__file__).resolve().parent.parent  # open-source/sdk-python/
    out_dir = tmp_path / "dist"
    out_dir.mkdir()
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(out_dir)],
        cwd=str(sdk_dir),
        check=True,
        capture_output=True,
    )
    wheels = list(out_dir.glob("juvera_sdk-*.whl"))
    assert wheels, "no wheel built"
    with zipfile.ZipFile(wheels[0]) as zf:
        names = zf.namelist()
    assert any(n.endswith("juvera_sdk/templates/report.html.j2") for n in names), \
        f"template missing from wheel; names={names}"
    assert any(n.endswith("juvera_sdk/data/model_pricing.json") for n in names), \
        f"pricing catalog missing from wheel; names={names}"
