"""Context variable storage for work items and request-scoped data."""
from __future__ import annotations
from contextvars import ContextVar

_work_item_id: ContextVar[str | None] = ContextVar("juvera_work_item_id", default=None)
_agent_id: ContextVar[str | None] = ContextVar("juvera_agent_id", default=None)
_workflow_type: ContextVar[str | None] = ContextVar("juvera_workflow_type", default=None)


def get_work_item_id() -> str | None:
    return _work_item_id.get()


def set_work_item_id(value: str | None):
    return _work_item_id.set(value)


def get_agent_id() -> str | None:
    return _agent_id.get()


def set_agent_id(value: str | None):
    return _agent_id.set(value)


def get_workflow_type() -> str | None:
    return _workflow_type.get()


def set_work_item(work_item_id: str, workflow_type: str | None = None) -> None:
    if not isinstance(work_item_id, str) or not work_item_id:
        raise ValueError("work_item_id must be a non-empty string")
    _work_item_id.set(work_item_id)
    _workflow_type.set(workflow_type)


def clear_work_item() -> None:
    _work_item_id.set(None)
    _workflow_type.set(None)
