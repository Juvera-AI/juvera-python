"""CI guard: every juvera_sdk/baselines/*.md must match WORKFLOW_BASELINES in roi.py.

If you edit a baseline number in either side, you must update the other.
This test catches drift before merge.
"""
from __future__ import annotations

import re
import warnings
from datetime import date, timedelta
from pathlib import Path

import pytest
import yaml

from juvera_sdk.roi import WORKFLOW_BASELINES

REQUIRED_KEYS = {
    "workflow_type",
    "human_cost_usd",
    "human_cost_usd_range",
    "human_time_minutes",
    "human_time_minutes_range",
    "confidence",
    "sources",
    "method",
    "last_reviewed",
}

CONFIDENCE_VALUES = {"low", "medium", "high"}

BASELINES_DIR = (
    Path(__file__).parent.parent / "juvera_sdk" / "baselines"
)

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

# Explicit allowlist — every workflow that should have a baseline .md file.
# Adding/removing rows here is the deliberate way to introduce or retire a workflow type.
EXPECTED_WORKFLOWS = {
    "ticket_deflection",
    "lead_qualification",
    "document_review",
    "data_extraction",
    "code_review",
    "compliance_check",
    "content_generation",
}


def _parse_baseline_md(path: Path) -> dict:
    text = path.read_text()
    match = FRONTMATTER_RE.match(text)
    assert match, f"{path.name}: no YAML frontmatter found (must start with ---)"
    return yaml.safe_load(match.group(1))


def _all_baseline_files() -> list[Path]:
    """Return only files matching the explicit allowlist. CHANGELOG, README,
    templates, or stray .md files in the directory are intentionally ignored."""
    return sorted(
        p for p in BASELINES_DIR.glob("*.md") if p.stem in EXPECTED_WORKFLOWS
    )


def test_every_baseline_md_has_required_keys():
    for path in _all_baseline_files():
        fm = _parse_baseline_md(path)
        missing = REQUIRED_KEYS - set(fm.keys())
        assert not missing, f"{path.name}: missing frontmatter keys {missing}"


def test_workflow_type_matches_filename():
    for path in _all_baseline_files():
        fm = _parse_baseline_md(path)
        assert fm["workflow_type"] == path.stem, (
            f"{path.name}: workflow_type={fm['workflow_type']!r} != filename stem {path.stem!r}"
        )


def test_confidence_is_valid():
    for path in _all_baseline_files():
        fm = _parse_baseline_md(path)
        assert fm["confidence"] in CONFIDENCE_VALUES, (
            f"{path.name}: confidence={fm['confidence']!r} not in {CONFIDENCE_VALUES}"
        )


def test_ranges_well_formed():
    for path in _all_baseline_files():
        fm = _parse_baseline_md(path)
        cost_lo, cost_hi = fm["human_cost_usd_range"]
        time_lo, time_hi = fm["human_time_minutes_range"]
        assert cost_lo < cost_hi, f"{path.name}: cost range invalid"
        assert time_lo < time_hi, f"{path.name}: time range invalid"
        cost_mid = fm["human_cost_usd"]
        time_mid = fm["human_time_minutes"]
        # Midpoint must lie within the [low, high] range
        assert cost_lo <= cost_mid <= cost_hi, (
            f"{path.name}: cost midpoint {cost_mid} outside range [{cost_lo}, {cost_hi}]"
        )
        assert time_lo <= time_mid <= time_hi, (
            f"{path.name}: time midpoint {time_mid} outside range [{time_lo}, {time_hi}]"
        )


def test_sources_non_empty_with_title_and_url():
    for path in _all_baseline_files():
        fm = _parse_baseline_md(path)
        sources = fm["sources"]
        assert isinstance(sources, list) and len(sources) >= 1, (
            f"{path.name}: must have ≥1 source"
        )
        for i, src in enumerate(sources):
            assert "title" in src and "url" in src, (
                f"{path.name}: source[{i}] missing title or url"
            )


# Keys whose presence indicates an entry has been migrated to the new annotation shape.
# Used to scope drift detection: legacy entries (still on {human_cost_usd, human_time_minutes} only)
# are excluded from sync until they're migrated, so the test stays green during incremental dev.
NEW_SHAPE_KEYS = frozenset({
    "human_cost_usd_range",
    "human_time_minutes_range",
    "confidence",
    "source_url",
    "last_reviewed",
})

# Fields that must match exactly between markdown frontmatter and WORKFLOW_BASELINES.
# This is the full mirrored set — adding/removing a field requires updating both sides.
MIRRORED_FIELDS = (
    "human_cost_usd",
    "human_time_minutes",
    "human_cost_usd_range",
    "human_time_minutes_range",
    "confidence",
    "last_reviewed",
)


def _migrated_workflow_types() -> set[str]:
    """WORKFLOW_BASELINES entries that have been migrated to the new annotation shape."""
    return {
        wt for wt, entry in WORKFLOW_BASELINES.items()
        if NEW_SHAPE_KEYS.issubset(entry.keys())
    }


def test_workflow_baselines_dict_matches_md():
    """Every migrated WORKFLOW_BASELINES entry must have a matching .md file with all
    mirrored fields equal. Legacy entries (still on cost+time only) are excluded so this
    test stays green during incremental migration across Stages A → C."""
    md_workflow_types = {p.stem for p in _all_baseline_files()}
    dict_workflow_types_migrated = _migrated_workflow_types()

    only_in_dict = dict_workflow_types_migrated - md_workflow_types
    only_in_md = md_workflow_types - dict_workflow_types_migrated
    assert not only_in_dict, (
        f"WORKFLOW_BASELINES has migrated entries with no .md file: {only_in_dict}"
    )
    assert not only_in_md, (
        f"juvera_sdk/baselines/ has .md files but their WORKFLOW_BASELINES entries "
        f"are not yet migrated to the new annotation shape: {only_in_md}"
    )

    for path in _all_baseline_files():
        fm = _parse_baseline_md(path)
        wt = fm["workflow_type"]
        dict_entry = WORKFLOW_BASELINES[wt]
        for key in MIRRORED_FIELDS:
            # PyYAML may decode last_reviewed as date or string; normalize both sides.
            md_val = fm[key]
            dict_val = dict_entry[key]
            if key == "last_reviewed":
                md_val = str(md_val)
                dict_val = str(dict_val)
            assert dict_val == md_val, (
                f"{wt}: dict[{key}]={dict_val!r} != md[{key}]={md_val!r}"
            )
        # source_url in dict must match juvera.ai/baselines anchor for this workflow
        expected_source_url = f"https://juvera.ai/baselines#{wt}"
        assert dict_entry["source_url"] == expected_source_url, (
            f"{wt}: dict source_url={dict_entry['source_url']!r} "
            f"!= expected {expected_source_url!r}"
        )


def test_all_expected_workflows_migrated_by_phase_end():
    """Release-readiness gate: every EXPECTED_WORKFLOWS entry must be migrated to the
    new annotation shape AND have a markdown file. Skipped during incremental dev
    (Stages A → mid-C) by setting JUVERA_BASELINE_PARTIAL_OK=1 in the environment;
    enforced unconditionally in CI on the feature branch before PR merge."""
    import os
    if os.environ.get("JUVERA_BASELINE_PARTIAL_OK") == "1":
        pytest.skip("incremental development; full coverage gate disabled")

    migrated = _migrated_workflow_types()
    md_types = {p.stem for p in _all_baseline_files()}
    missing_in_dict = EXPECTED_WORKFLOWS - migrated
    missing_in_md = EXPECTED_WORKFLOWS - md_types
    assert not missing_in_dict, (
        f"workflows not yet migrated in WORKFLOW_BASELINES: {missing_in_dict}"
    )
    assert not missing_in_md, (
        f"workflows missing .md file in juvera_sdk/baselines/: {missing_in_md}"
    )


README_TABLE_ROW_RE = re.compile(
    r"^\|\s*`(?P<wf>\w+)`\s*\|\s*\$(?P<cost>\d+(?:\.\d+)?)\s*\|\s*(?P<time>\d+)\s*min\s*\|\s*$",
    re.MULTILINE,
)


def test_readme_roi_table_matches_workflow_baselines():
    """The ROI table in README.md must match WORKFLOW_BASELINES midpoints.

    Guards the "internal contradiction from a partial edit" failure mode:
    if someone updates roi.py and the surrounding README prose but misses
    the canonical workflow_type | cost | time table, this test catches it.

    Caught in PR #203 review: code_review dropped to $50 in roi.py + the
    surrounding paragraph + override example, but the table row 8 lines
    below still said $95.
    """
    readme = (
        Path(__file__).parent.parent / "README.md"
    ).read_text()
    rows = list(README_TABLE_ROW_RE.finditer(readme))
    workflows_in_table = {m.group("wf") for m in rows}
    assert workflows_in_table == EXPECTED_WORKFLOWS, (
        f"README ROI table workflows {workflows_in_table} != "
        f"EXPECTED_WORKFLOWS {EXPECTED_WORKFLOWS}"
    )
    for m in rows:
        wf = m.group("wf")
        readme_cost = float(m.group("cost"))
        readme_time = int(m.group("time"))
        dict_cost = WORKFLOW_BASELINES[wf]["human_cost_usd"]
        dict_time = WORKFLOW_BASELINES[wf]["human_time_minutes"]
        assert readme_cost == dict_cost, (
            f"README ROI table {wf}: cost=${readme_cost} != dict ${dict_cost}"
        )
        assert readme_time == dict_time, (
            f"README ROI table {wf}: time={readme_time} min != dict {dict_time} min"
        )


def test_last_reviewed_not_stale():
    """Soft warn (do not fail) when a baseline is > 12 months stale.

    NOTE: this test takes NO fixture parameter. Using pytest's `recwarn` fixture
    here would silently capture the warning into the fixture object and prevent
    it from appearing in pytest's warnings summary — defeating the soft-signal
    intent. With no fixture, `warnings.warn(UserWarning)` propagates to
    pytest's default warning collection, which DOES surface in the test report
    (and CI logs) without failing the suite (provided no `-W error::UserWarning`
    is configured — see CI section of the spec).
    """
    cutoff = date.today() - timedelta(days=365)
    for path in _all_baseline_files():
        fm = _parse_baseline_md(path)
        last_reviewed = fm["last_reviewed"]
        # PyYAML decodes ISO date strings to datetime.date automatically
        if isinstance(last_reviewed, str):
            last_reviewed = date.fromisoformat(last_reviewed)
        if last_reviewed < cutoff:
            warnings.warn(
                f"{path.name}: last_reviewed={last_reviewed} is > 12 months old",
                UserWarning,
                stacklevel=2,
            )
