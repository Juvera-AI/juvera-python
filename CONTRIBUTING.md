# Contributing to juvera-python

Thanks for your interest in contributing. This is a focused instrumentation SDK — keep that scope in mind when proposing changes.

## What belongs here

- Bug fixes in the SDK core (`juvera_sdk/`)
- New model cost entries in `costs.py`
- New examples in `examples/`
- Test coverage improvements
- Documentation improvements

## What does not belong here

- Attribution logic (server-side, closed source)
- Benchmarking or evaluation features
- Any reference to private Juvera API endpoints beyond `/v1/traces` and `/v1/impact-signals`

## Setup

```bash
git clone https://github.com/Juvera-AI/juvera-python
cd juvera-python
pip install -e ".[dev]"
```

## Running tests

```bash
pytest -v
```

All 18 tests must pass before submitting a PR.

## Submitting a PR

1. Fork the repo and create a branch: `git checkout -b fix/your-fix`
2. Make your change and add or update tests
3. Run `pytest -v` — all tests must pass
4. Open a PR against `main` with a clear description of what changed and why

## Code style

- Follow existing patterns in the codebase
- `from __future__ import annotations` at the top of every module (Python 3.9 compatibility)
- Use `Optional[X]` not `X | None` in Pydantic model fields (Pydantic evaluates annotations at runtime)
- No docstrings required unless the logic is non-obvious

## Reporting bugs

Open a GitHub issue with:
- Python version
- `juvera-sdk` version (`pip show juvera-sdk`)
- Minimal reproduction script
- What you expected vs. what happened
