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
import sys
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


# ──────────────────────────────────────────────────────────────────────────────
# Per-command flag allowlist (Task 7.2)
# ──────────────────────────────────────────────────────────────────────────────
#
# Per-command allowlist of flag presence indicators that may appear in telemetry.
# Values are NEVER transmitted; only the boolean presence as the listed name.
# Adding a new flag to the CLI without updating this list = silently excluded.

from typing import Callable

_FLAG_ALLOWLIST: dict[str, dict[str, Callable]] = {
    "demo": {
        "no_save":      lambda ns: bool(getattr(ns, "no_save", False)),
        "live":         lambda ns: bool(getattr(ns, "live", False)),
        "seed_set":     lambda ns: getattr(ns, "seed", None) is not None,
        "workflow_set": lambda ns: getattr(ns, "workflow", "ticket_deflection") != "ticket_deflection",
    },
    "listen": {
        "local":        lambda ns: bool(getattr(ns, "local", False)),
        "cloud_set":    lambda ns: bool(getattr(ns, "api_key", None)),
        "port_default": lambda ns: getattr(ns, "port", 4318) == 4318,
    },
    "report": {
        "format_set":   lambda ns: getattr(ns, "format", "html") != "html",
        "source_set":   lambda ns: getattr(ns, "source", "all") != "all",
        "since_set":    lambda ns: getattr(ns, "since", "30d") != "30d",
        "no_open":      lambda ns: bool(getattr(ns, "no_open", False)),
        "output_set":   lambda ns: getattr(ns, "output", None) is not None,
    },
    "doctor": {
        "scan_ports":   lambda ns: bool(getattr(ns, "scan_ports", False)),
    },
    "validate": {},
    "patch": {
        "cwd_set":      lambda ns: getattr(ns, "cwd", ".") != ".",
    },
    "config": {
        "key_set":      lambda ns: getattr(ns, "key", None) is not None,
    },
}


def build_flags_used(command: str, args) -> list[str]:
    """Return list of allowlisted flag presence names for the given command.

    Flag values are NEVER included. Names not in the allowlist are silently
    excluded (defense in depth — adding a new flag without updating the
    allowlist results in it being dropped from telemetry rather than leaked).
    """
    allow = _FLAG_ALLOWLIST.get(command, {})
    return [name for name, predicate in allow.items() if predicate(args)]


# ──────────────────────────────────────────────────────────────────────────────
# Consent prompt (Task 7.3) — deferred until AFTER primary command output
# ──────────────────────────────────────────────────────────────────────────────

_PROMPT_TEXT = """
Help improve Juvera? Share anonymous usage stats:
  juvera version, OS/arch, command name, outcome/duration, allowlisted flag names only.
Never sent: prompts, completions, file paths, API keys, flag values, costs, workflow types.

Enable? [y/N] (change anytime: juvera config set telemetry false)
"""


def maybe_prompt_consent() -> None:
    """Show the consent prompt on first run. No-op if already prompted.

    Must be called AFTER the primary command output has been printed and stdout
    flushed, so the ROI card / report path / banner is the first thing the user sees.
    """
    from juvera_sdk.user_config import load_config, set_value

    cfg = load_config()
    if cfg.get("prompted"):
        return

    if not sys.stdin.isatty():
        # Non-interactive (CI, piped): default to disabled, mark as prompted.
        set_value("prompted", True)
        return

    print(_PROMPT_TEXT)
    try:
        answer = input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = ""
    enabled = answer in ("y", "yes")
    set_value("telemetry", enabled)
    set_value("prompted", True)


# ──────────────────────────────────────────────────────────────────────────────
# Telemetry sender (Task 7.4) — fire-and-forget; no-op without endpoint
# ──────────────────────────────────────────────────────────────────────────────

import httpx
import platform
import secrets


def _new_event_id() -> str:
    """Generate a 26-char random ID (ULID-shaped)."""
    alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    return "".join(secrets.choice(alphabet) for _ in range(26))


def send_event(
    *, command: str, outcome: str, duration_ms: int, flags_used: list[str],
    timeout: float = 2.0,
) -> bool:
    """Fire-and-forget anonymous telemetry. No-op if not opted in or no endpoint.

    Args:
        command: command name (e.g. 'demo', 'listen', 'report')
        outcome: 'success' or 'error'
        duration_ms: command execution time in milliseconds
        flags_used: allowlisted flag presence names (never values)
        timeout: HTTP request timeout in seconds

    Returns:
        True if the telemetry was sent successfully, False otherwise.
        Network errors are swallowed silently; the caller should not retry.
    """
    from juvera_sdk.user_config import load_config

    cfg = load_config()
    if not cfg.get("telemetry"):
        return False
    endpoint = cfg.get("telemetry_endpoint")
    if not endpoint:
        return False

    try:
        from juvera_sdk import __version__ as _ver
    except (ImportError, AttributeError):
        _ver = "unknown"

    payload = {
        "schema_version": "1",
        "install_id": cfg["install_id"],
        "event_id": _new_event_id(),
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "outcome": outcome,
        "duration_ms": duration_ms,
        "os": platform.system().lower(),
        "arch": platform.machine().lower(),
        "python_version": platform.python_version(),
        "juvera_sdk_version": _ver,
        "flags_used": flags_used,
    }
    try:
        with httpx.Client(timeout=timeout) as c:
            r = c.post(endpoint, json=payload)
            return r.status_code < 400
    except httpx.HTTPError:
        return False
