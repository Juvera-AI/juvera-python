import subprocess
import sys
import time
import signal
import os


def _start(args, env=None):
    return subprocess.Popen(
        [sys.executable, "-m", "juvera_sdk.cli", "listen", *args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
    )


def test_listen_keyless_prints_local_capture_only_banner(tmp_path):
    env = {"HOME": str(tmp_path), "PATH": os.environ.get("PATH", ""),
           "NO_COLOR": "1"}
    p = _start(["--port", "0"], env=env)
    time.sleep(1.0)
    p.send_signal(signal.SIGINT)
    out, err = p.communicate(timeout=10)
    combined = out + err
    assert "LOCAL CAPTURE ONLY" in combined, f"banner missing. stdout={out!r} stderr={err!r}"
    assert "no JUVERA_API_KEY" in combined or "no juvera_api_key" in combined.lower()


def test_listen_with_api_key_prints_cloud_upload_banner(tmp_path):
    env = {"HOME": str(tmp_path), "PATH": os.environ.get("PATH", ""),
           "JUVERA_API_KEY": "jvr_test_only", "JUVERA_ORG_ID": "org_test",
           "NO_COLOR": "1"}
    p = _start(["--port", "0"], env=env)
    time.sleep(1.0)
    p.send_signal(signal.SIGINT)
    out, err = p.communicate(timeout=10)
    combined = out + err
    assert "LOCAL + CLOUD UPLOAD" in combined, f"banner missing. stdout={out!r} stderr={err!r}"


def test_listen_local_flag_overrides_env_key(tmp_path):
    env = {"HOME": str(tmp_path), "PATH": os.environ.get("PATH", ""),
           "JUVERA_API_KEY": "jvr_test_only", "JUVERA_ORG_ID": "org_test",
           "NO_COLOR": "1"}
    p = _start(["--port", "0", "--local"], env=env)
    time.sleep(1.0)
    p.send_signal(signal.SIGINT)
    out, err = p.communicate(timeout=10)
    combined = out + err
    assert "LOCAL CAPTURE ONLY" in combined
