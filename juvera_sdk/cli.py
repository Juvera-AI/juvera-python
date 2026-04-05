"""CLI entrypoint for Juvera Local Relay and validation helpers."""
from __future__ import annotations

import argparse
import os

from juvera_sdk.local_relay import (
    DEFAULT_HOST,
    DEFAULT_INGEST_ENDPOINT,
    DEFAULT_PORT,
    run_doctor,
    run_listen,
    run_patch,
    run_validate,
)


def main() -> int:
    parser = argparse.ArgumentParser(prog="juvera")
    subparsers = parser.add_subparsers(dest="command", required=True)

    listen = subparsers.add_parser("listen", help="Start Juvera Local Relay on loopback.")
    listen.add_argument("--host", default=DEFAULT_HOST)
    listen.add_argument("--port", type=int, default=DEFAULT_PORT)
    listen.add_argument("--ingest-endpoint", default=os.getenv("JUVERA_INGEST_ENDPOINT", DEFAULT_INGEST_ENDPOINT))
    listen.add_argument("--api-base-url", default=os.getenv("JUVERA_API_BASE_URL", "http://localhost:8000"))
    listen.add_argument("--api-key", default=os.getenv("JUVERA_API_KEY"))
    listen.add_argument("--org-id", default=os.getenv("JUVERA_ORG_ID"))
    listen.add_argument("--setup-token", default=os.getenv("JUVERA_SETUP_TOKEN"))
    listen.add_argument("--environment", default=os.getenv("JUVERA_ENVIRONMENT", "local"))
    listen.set_defaults(func=run_listen)

    doctor = subparsers.add_parser("doctor", help="Check relay health and optionally probe common local dev ports.")
    doctor.add_argument("--base-url", default=f"http://{DEFAULT_HOST}:{DEFAULT_PORT}")
    doctor.add_argument("--scan-ports", action="store_true")
    doctor.set_defaults(func=run_doctor)

    validate = subparsers.add_parser("validate", help="Validate the latest relay capture for attribution readiness.")
    validate.add_argument("--base-url", default=f"http://{DEFAULT_HOST}:{DEFAULT_PORT}")
    validate.set_defaults(func=run_validate)

    patch = subparsers.add_parser("patch", help="Show the recommended upgrade path from proxy mode to SDK instrumentation.")
    patch.add_argument("--base-url", default=f"http://{DEFAULT_HOST}:{DEFAULT_PORT}")
    patch.add_argument("--cwd", default=".")
    patch.set_defaults(func=run_patch)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
