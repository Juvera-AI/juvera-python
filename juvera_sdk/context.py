"""Context variable storage for work items and request-scoped data."""
from __future__ import annotations
from contextvars import ContextVar

_work_item_id: ContextVar[str | None] = ContextVar("juvera_work_item_id", default=None)
_agent_id: ContextVar[str | None] = ContextVar("juvera_agent_id", default=None)


def get_work_item_id() -> str | None:
    return _work_item_id.get()


def set_work_item_id(value: str | None):
    return _work_item_id.set(value)


def get_agent_id() -> str | None:
    return _agent_id.get()


def set_agent_id(value: str | None):
    return _agent_id.set(value)
