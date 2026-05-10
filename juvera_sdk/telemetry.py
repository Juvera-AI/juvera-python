"""Telemetry: consent prompt + flag allowlist + sender + local metrics counters.

This file accumulates four discrete concerns across Tasks 7.1–7.4:
- Local metrics counters (this task)
- Per-command flag allowlist (Task 7.2)
- Consent prompt (Task 7.3)
- Fire-and-forget HTTP sender (Task 7.4)
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from juvera_sdk.local_storage import juvera_root


# ──────────────────────────────────────────────────────────────────────────────
# Local metrics counters (Task 7.1)
# ──────────────────────────────────────────────────────────────────────────────

def metrics_path() -> Path:
    return juvera_root() / "metrics.json"


def load_counters() -> dict[str, Any]:
    """Load metrics; return empty-shaped dict if missing or corrupt."""
    p = metrics_path()
    if not p.is_file():
        return {"schema_version": "1", "first_run_at": None, "counts": {}, "last_used": {}}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"schema_version": "1", "first_run_at": None, "counts": {}, "last_used": {}}


def _atomic_write(data: dict[str, Any]) -> None:
    p = metrics_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".metrics-", suffix=".tmp", dir=str(p.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(tmp, p)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def increment_counter(command: str) -> None:
    """Increment the counter for `command` and update its last_used timestamp."""
    m = load_counters()
    now = datetime.now(timezone.utc).isoformat()
    if not m.get("first_run_at"):
        m["first_run_at"] = now
    m.setdefault("counts", {})[command] = m["counts"].get(command, 0) + 1
    m.setdefault("last_used", {})[command] = now
    _atomic_write(m)
