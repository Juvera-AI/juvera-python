import json
from pathlib import Path

import pytest

from juvera_sdk.user_config import (
    config_path,
    load_config,
    get_value,
    set_value,
    unset_value,
    DEFAULTS,
    InvalidConfigKey,
    InvalidConfigType,
)


def test_config_path_under_juvera_root(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert config_path() == tmp_path / ".juvera" / "config.json"


def test_load_config_returns_defaults_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config()
    assert cfg["telemetry"] is False
    assert cfg["prompted"] is False
    assert "install_id" in cfg  # auto-generated


def test_set_and_get_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    set_value("telemetry", True)
    assert get_value("telemetry") is True
    cfg = load_config()
    assert cfg["telemetry"] is True


def test_set_rejects_unknown_key(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    with pytest.raises(InvalidConfigKey):
        set_value("not_a_real_key", "anything")


def test_set_rejects_wrong_type(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    with pytest.raises(InvalidConfigType):
        set_value("telemetry", "not a bool")


def test_unset_reverts_to_default(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    set_value("telemetry", True)
    unset_value("telemetry")
    assert get_value("telemetry") == DEFAULTS["telemetry"]


def test_install_id_generated_once_and_stable(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    a = get_value("install_id")
    b = get_value("install_id")
    assert a == b
    assert len(a) == 26  # ULID


def test_set_install_id_rejected(tmp_path, monkeypatch):
    """install_id is system-managed; set_value must reject it."""
    monkeypatch.setenv("HOME", str(tmp_path))
    with pytest.raises(InvalidConfigKey):
        set_value("install_id", "DEADBEEF" * 4)


def test_unset_install_id_rotates(tmp_path, monkeypatch):
    """unset_value('install_id') generates a new id rather than leaving None."""
    monkeypatch.setenv("HOME", str(tmp_path))
    original = get_value("install_id")
    unset_value("install_id")
    new_id = get_value("install_id")
    assert new_id != original
    assert len(new_id) == 26
