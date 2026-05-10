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
        try:
            path = capture_path_for(source="demo", run_id=run["event_id"])
            event = {**run}
            event["captured_at"] = datetime.now(timezone.utc).isoformat()
            event.pop("_user_message", None)
            write_capture_event(path, event)
        except OSError as e:
            print(f"  (warning: could not save capture: {e})", file=sys.stderr)

    print(render_roi_card(run, color=_should_use_color(), unicode=_should_use_unicode()))
    sys.stdout.flush()

    if not args.no_save:
        from juvera_sdk.local_storage import read_captures
        n = sum(1 for _ in read_captures(source="demo"))
        if n > 1:
            print(f"\n  ({n} demo captures stored — 'juvera report' will aggregate all of them)")

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


def _since_to_cutoffs(since: str) -> tuple[str | None, str | None]:
    """Return (date_cutoff_for_dirs, iso_cutoff_for_events).

    date cutoff is YYYY-MM-DD for skipping older date directories cheaply.
    iso cutoff is full ISO 8601 for per-event timestamp filtering — preserves
    hour-level precision that 'YYYY-MM-DD' alone would lose for --since 24h.
    """
    from datetime import timedelta
    if since == "all":
        return None, None
    n_str, unit = since[:-1], since[-1]
    n = int(n_str)
    delta = {"h": timedelta(hours=n), "d": timedelta(days=n)}[unit]
    cutoff = datetime.now(timezone.utc) - delta
    return cutoff.strftime("%Y-%m-%d"), cutoff.isoformat()


def run_report(args) -> int:
    import webbrowser
    from pathlib import Path
    from juvera_sdk.local_storage import read_captures, reports_root
    from juvera_sdk.report import filter_events, render_html, build_report_context

    date_cutoff, iso_cutoff = _since_to_cutoffs(args.since)
    source = None if args.source == "all" else args.source
    events = list(filter_events(
        read_captures(since_date=date_cutoff, source=source),
        since_date=iso_cutoff,   # finer per-event filter (hour precision)
        source=source,
    ))

    if args.source == "capture" and not events:
        print(
            "  (note: --source capture matches no events yet. 'juvera listen' will start "
            "writing local captures in v0.2.0 (Task 6.1). Use --source demo or --source all "
            "to see existing data.)",
            file=sys.stderr,
        )

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if args.format == "md":
        ctx = build_report_context(events, window_label=f"last {args.since}")
        content = (
            f"# Juvera ROI Report\n\n"
            f"Generated {ctx['generated_at']}\n\n"
            f"- Total runs: {ctx['total_runs']}\n"
            f"- Total estimated savings: +${ctx['total_savings']:.4f}\n"
            f"- Top workflow: {ctx['top_workflow']}\n"
            f"- Unattributed: {ctx['unattributed_runs']}\n"
        )
        out = args.output or str(reports_root() / f"{today}-report.md")
    else:
        content = render_html(events, window_label=f"last {args.since}")
        out = args.output or str(reports_root() / f"{today}-report.html")

    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(content, encoding="utf-8")

    print(f"Report written to {out}")
    if args.format == "html" and not args.no_open:
        try:
            webbrowser.open(f"file://{out}")
        except Exception:
            pass
    return 0


def _add_report_subparser(subparsers) -> None:
    rep = subparsers.add_parser("report", help="Render an HTML ROI report from local captures.")
    rep.add_argument("--since", default="30d", help="Time window: '24h', '7d', '30d', 'all'.")
    rep.add_argument("--source", choices=["demo", "capture", "all"], default="all",
                     help="Filter capture source. 'capture' is populated once 'juvera listen' "
                          "writes to local storage (Task 6.1 — landing soon).")
    rep.add_argument("--format", choices=["html", "md"], default="html")
    rep.add_argument("--output", default=None, help="Override output file path.")
    rep.add_argument("--no-open", action="store_true", help="Skip auto-open in browser.")
    rep.set_defaults(func=run_report)


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
    _add_report_subparser(subparsers)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
