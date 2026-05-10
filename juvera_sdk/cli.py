"""CLI entrypoint for Juvera Local Relay and validation helpers."""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone

from juvera_sdk.local_relay import (
    DEFAULT_HOST,
    DEFAULT_INGEST_ENDPOINT,
    DEFAULT_PORT,
    run_doctor,
    run_listen,
    run_patch,
    run_validate,
)


def _should_use_color() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _should_use_unicode() -> bool:
    import os
    if "UTF-8" in os.environ.get("LANG", ""):
        return True
    encoding = sys.stdout.encoding or ""
    return encoding.lower().startswith("utf")


def run_demo(args) -> int:
    if args.live:
        import warnings
        warnings.warn(
            "--live is not yet implemented; running simulation. "
            "Live mode will hit OPENAI_API_KEY/ANTHROPIC_API_KEY-backed model in a future release.",
            stacklevel=2,
        )
    from juvera_sdk.demo import generate_synthetic_run, render_roi_card
    from juvera_sdk.local_storage import capture_path_for, write_capture_event

    run = generate_synthetic_run(workflow_type=args.workflow, seed=args.seed)
    if not args.no_save:
        path = capture_path_for(source="demo", run_id=run["event_id"])
        event = {**run}
        event["captured_at"] = datetime.now(timezone.utc).isoformat()
        event.pop("_user_message", None)
        write_capture_event(path, event)

    print(render_roi_card(run, color=_should_use_color(), unicode=_should_use_unicode()))
    sys.stdout.flush()
    return 0


def _add_demo_subparser(subparsers) -> None:
    demo = subparsers.add_parser("demo", help="Simulate one agent run and print an ROI card.")
    demo.add_argument("--no-save", action="store_true", help="Don't write NDJSON.")
    demo.add_argument("--workflow", default="ticket_deflection",
                      help="Workflow baseline to simulate.")
    demo.add_argument("--seed", type=int, default=None,
                      help="Seed RNG for deterministic output.")
    demo.add_argument("--live", action="store_true",
                      help="If OPENAI/ANTHROPIC API key is set, hit the real model.")
    demo.set_defaults(func=run_demo)


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
    listen.add_argument("--setup-id", default=os.getenv("JUVERA_SETUP_ID"))
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

    _add_demo_subparser(subparsers)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
