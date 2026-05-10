"""~/.juvera/config.json get/set/unset with atomic write."""
from __future__ import annotations

import json
import os
import secrets
import tempfile
from pathlib import Path
from typing import Any

from juvera_sdk.local_storage import juvera_root


class InvalidConfigKey(Exception):
    pass


class InvalidConfigType(Exception):
    pass


# Allowlisted config keys with their expected Python types and defaults.
SCHEMA: dict[str, dict[str, Any]] = {
    "telemetry": {"type": bool, "default": False, "internal": False},
    "telemetry_endpoint": {"type": (str, type(None)), "default": None, "internal": False},
    "prompted": {"type": bool, "default": False, "internal": False},
    "install_id": {"type": str, "default": None, "internal": True},  # auto-generated on first read
}

DEFAULTS = {k: v["default"] for k, v in SCHEMA.items()}


def _new_install_id() -> str:
    """26-char URL-safe random id (ULID-shaped). Not a real ULID — just opaque."""
    alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    return "".join(secrets.choice(alphabet) for _ in range(26))


def config_path() -> Path:
    return juvera_root() / "config.json"


def load_config() -> dict[str, Any]:
    """Load config; merge in defaults; auto-generate install_id if absent."""
    path = config_path()
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    else:
        data = {}
    merged = dict(DEFAULTS)
    merged.update({k: v for k, v in data.items() if k in SCHEMA})
    if not merged.get("install_id"):
        merged["install_id"] = _new_install_id()
        _atomic_write(merged)
    return merged


def get_value(key: str) -> Any:
    if key not in SCHEMA:
        raise InvalidConfigKey(f"Unknown config key: {key!r}")
    return load_config()[key]


def set_value(key: str, value: Any) -> None:
    if key not in SCHEMA:
        raise InvalidConfigKey(
            f"Unknown config key: {key!r}. Known: {sorted(SCHEMA.keys())}"
        )
    if SCHEMA[key].get("internal"):
        raise InvalidConfigKey(
            f"Config key {key!r} is system-managed and cannot be set directly."
        )
    expected = SCHEMA[key]["type"]
    if not isinstance(value, expected):
        raise InvalidConfigType(
            f"Key {key!r} expects type {expected}, got {type(value).__name__}"
        )
    cfg = load_config()
    cfg[key] = value
    _atomic_write(cfg)


def unset_value(key: str) -> None:
    """Reset a key to its default value.

    Special case for `install_id`: rather than reverting to None (which would
    cause the next load_config() to silently generate a new id anyway), this
    eagerly rotates to a fresh install_id immediately. This makes the rotation
    explicit and observable.
    """
    if key not in SCHEMA:
        raise InvalidConfigKey(f"Unknown config key: {key!r}")
    cfg = load_config()
    cfg[key] = SCHEMA[key]["default"]
    if key == "install_id":
        cfg[key] = _new_install_id()
    _atomic_write(cfg)


def _atomic_write(cfg: dict[str, Any]) -> None:
    """Write atomically: tempfile in same dir, then rename."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".config-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
