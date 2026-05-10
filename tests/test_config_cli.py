import subprocess
import sys
import os
import json


def _run(args, env=None):
    return subprocess.run(
        [sys.executable, "-m", "juvera_sdk.cli", *args],
        capture_output=True, text=True, env=env,
    )


def test_config_get_default_telemetry(tmp_path):
    env = {"HOME": str(tmp_path), "PATH": os.environ.get("PATH", "")}
    r = _run(["config", "get", "telemetry"], env=env)
    assert r.returncode == 0, r.stderr
    assert "false" in r.stdout.lower()


def test_config_set_then_get_round_trip(tmp_path):
    env = {"HOME": str(tmp_path), "PATH": os.environ.get("PATH", "")}
    r = _run(["config", "set", "telemetry", "true"], env=env)
    assert r.returncode == 0, r.stderr
    r = _run(["config", "get", "telemetry"], env=env)
    assert "true" in r.stdout.lower()


def test_config_set_invalid_key(tmp_path):
    env = {"HOME": str(tmp_path), "PATH": os.environ.get("PATH", "")}
    r = _run(["config", "set", "no_such_key", "x"], env=env)
    assert r.returncode != 0
    assert "unknown" in r.stderr.lower()


def test_config_set_install_id_rejected(tmp_path):
    """install_id is system-managed; set_value rejects it."""
    env = {"HOME": str(tmp_path), "PATH": os.environ.get("PATH", "")}
    r = _run(["config", "set", "install_id", "DEADBEEF" * 4], env=env)
    assert r.returncode != 0
    assert "system-managed" in r.stderr.lower() or "cannot be set" in r.stderr.lower()


def test_config_get_all(tmp_path):
    env = {"HOME": str(tmp_path), "PATH": os.environ.get("PATH", "")}
    r = _run(["config", "get"], env=env)
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert "telemetry" in data
    assert "install_id" in data


def test_config_unset_telemetry_reverts_to_default(tmp_path):
    env = {"HOME": str(tmp_path), "PATH": os.environ.get("PATH", "")}
    _run(["config", "set", "telemetry", "true"], env=env)
    r = _run(["config", "unset", "telemetry"], env=env)
    assert r.returncode == 0, r.stderr
    r = _run(["config", "get", "telemetry"], env=env)
    assert "false" in r.stdout.lower()
