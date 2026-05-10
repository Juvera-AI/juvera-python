"""Local NDJSON storage for ~/.juvera/captures/<date>/<source>-<ulid>.ndjson."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def juvera_root() -> Path:
    """Return ~/.juvera, honoring $HOME for tests."""
    return Path(os.environ.get("HOME", str(Path.home()))) / ".juvera"


def captures_root() -> Path:
    return juvera_root() / "captures"


def reports_root() -> Path:
    return juvera_root() / "reports"


def capture_path_for(*, source: str, run_id: str, date: str | None = None) -> Path:
    """Return the NDJSON file path for a given source ('demo'|'capture') and run id.

    File layout: ~/.juvera/captures/YYYY-MM-DD/<source>-<run_id>.ndjson
    """
    if source not in ("demo", "capture"):
        raise ValueError(f"source must be 'demo' or 'capture', got {source!r}")
    d = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return captures_root() / d / f"{source}-{run_id}.ndjson"


def write_capture_event(path: Path, event: dict[str, Any]) -> None:
    """Append one JSON event as a line. Creates parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, separators=(",", ":")) + "\n")


def read_captures(
    *,
    since_date: str | None = None,
    source: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield all capture events across files, skipping corrupted lines.

    `since_date` (YYYY-MM-DD): include only files in date directories >= this date.
    `source` ('demo'|'capture'): include only files matching this source.
    """
    root = captures_root()
    if not root.exists():
        return
    for date_dir in sorted(root.iterdir()):
        if not date_dir.is_dir():
            continue
        if since_date and date_dir.name < since_date:
            continue
        for ndjson_file in sorted(date_dir.iterdir()):
            if not ndjson_file.name.endswith(".ndjson"):
                continue
            if source and not ndjson_file.name.startswith(f"{source}-"):
                continue
            with ndjson_file.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue  # skip corrupt line
