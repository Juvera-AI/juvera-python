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


def test_since_filter_respects_iso_datetime():
    """Full ISO datetime cutoff must filter at hour precision, not just date."""
    events = [
        {"captured_at": "2026-05-08T08:00:00+00:00", "source": "demo"},
        {"captured_at": "2026-05-08T14:00:00+00:00", "source": "demo"},
        {"captured_at": "2026-05-08T20:00:00+00:00", "source": "demo"},
    ]
    # Cutoff = noon on 2026-05-08; only afternoon events should pass.
    out = list(filter_events(events, since_date="2026-05-08T12:00:00+00:00"))
    assert len(out) == 2
    assert all(e["captured_at"] >= "2026-05-08T12:00:00+00:00" for e in out)
