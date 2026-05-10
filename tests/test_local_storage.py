import json
from pathlib import Path

from juvera_sdk.local_storage import (
    capture_path_for,
    write_capture_event,
    read_captures,
    juvera_root,
)


def test_juvera_root_uses_home_juvera(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert juvera_root() == tmp_path / ".juvera"


def test_capture_path_includes_date_and_source(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    p = capture_path_for(source="demo", run_id="01HXY2KQRM")
    assert p.parent.name.count("-") == 2  # YYYY-MM-DD
    assert p.name.startswith("demo-01HXY2KQRM")
    assert p.suffix == ".ndjson"


def test_write_capture_event_appends_jsonl(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    path = capture_path_for(source="demo", run_id="01TEST")
    write_capture_event(path, {"schema_version": "1", "event_id": "01EVT", "x": 1})
    write_capture_event(path, {"schema_version": "1", "event_id": "01EVT2", "x": 2})
    lines = path.read_text().strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0])["x"] == 1
    assert json.loads(lines[1])["x"] == 2


def test_read_captures_yields_all_events_across_files(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    p1 = capture_path_for(source="demo", run_id="01A")
    p2 = capture_path_for(source="capture", run_id="01B")
    write_capture_event(p1, {"schema_version": "1", "event_id": "e1"})
    write_capture_event(p2, {"schema_version": "1", "event_id": "e2"})
    events = list(read_captures())
    assert len(events) == 2
    assert {e["event_id"] for e in events} == {"e1", "e2"}


def test_read_captures_skips_corrupt_lines(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    p = capture_path_for(source="demo", run_id="01CORRUPT")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('{"event_id": "good1"}\n{not valid json\n{"event_id": "good2"}\n')
    events = list(read_captures())
    assert {e["event_id"] for e in events} == {"good1", "good2"}


def test_read_captures_since_date_filter(tmp_path, monkeypatch):
    """since_date excludes files in date directories older than the cutoff."""
    monkeypatch.setenv("HOME", str(tmp_path))
    old = capture_path_for(source="demo", run_id="01OLD", date="2026-04-01")
    new = capture_path_for(source="demo", run_id="01NEW", date="2026-05-01")
    write_capture_event(old, {"event_id": "e_old"})
    write_capture_event(new, {"event_id": "e_new"})

    events = list(read_captures(since_date="2026-05-01"))
    assert {e["event_id"] for e in events} == {"e_new"}, events


def test_read_captures_source_filter(tmp_path, monkeypatch):
    """source filter excludes files whose name doesn't start with that prefix."""
    monkeypatch.setenv("HOME", str(tmp_path))
    demo = capture_path_for(source="demo", run_id="01D", date="2026-05-01")
    cap = capture_path_for(source="capture", run_id="01C", date="2026-05-01")
    write_capture_event(demo, {"event_id": "e_demo"})
    write_capture_event(cap, {"event_id": "e_capture"})

    only_demo = list(read_captures(source="demo"))
    assert {e["event_id"] for e in only_demo} == {"e_demo"}

    only_capture = list(read_captures(source="capture"))
    assert {e["event_id"] for e in only_capture} == {"e_capture"}
