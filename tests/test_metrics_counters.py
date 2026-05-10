from juvera_sdk.telemetry import increment_counter, load_counters, metrics_path


def test_first_increment_creates_file_with_first_run_at(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    increment_counter("demo")
    m = load_counters()
    assert m["counts"]["demo"] == 1
    assert m["first_run_at"]


def test_multiple_increments_persist_across_loads(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    increment_counter("demo")
    increment_counter("demo")
    increment_counter("report")
    m = load_counters()
    assert m["counts"]["demo"] == 2
    assert m["counts"]["report"] == 1


def test_unknown_command_still_recorded(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    increment_counter("future_command")
    m = load_counters()
    assert m["counts"]["future_command"] == 1


def test_metrics_path_under_juvera_root(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert metrics_path() == tmp_path / ".juvera" / "metrics.json"


def test_load_counters_returns_empty_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    m = load_counters()
    assert m["counts"] == {}
    assert m["first_run_at"] is None
    assert m["last_used"] == {}
