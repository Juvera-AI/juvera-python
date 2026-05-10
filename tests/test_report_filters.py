from juvera_sdk.report import filter_events


SAMPLE = [
    {"captured_at": "2026-05-01T00:00:00Z", "source": "demo"},
    {"captured_at": "2026-05-08T00:00:00Z", "source": "capture"},
    {"captured_at": "2026-05-08T10:00:00Z", "source": "demo"},
]


def test_since_filter_excludes_older():
    out = list(filter_events(SAMPLE, since_date="2026-05-08"))
    assert len(out) == 2


def test_source_filter():
    out = list(filter_events(SAMPLE, source="capture"))
    assert len(out) == 1
    assert out[0]["source"] == "capture"
