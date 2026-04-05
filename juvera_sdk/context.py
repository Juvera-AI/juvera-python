"""Context variable storage for workflow, user, and request-scoped data."""
from __future__ import annotations

import inspect
from contextvars import ContextVar
from functools import wraps
from typing import Any, Callable

_work_item_id: ContextVar[str | None] = ContextVar("juvera_work_item_id", default=None)
_work_item_explicit: ContextVar[bool] = ContextVar("juvera_work_item_explicit", default=False)
_agent_id: ContextVar[str | None] = ContextVar("juvera_agent_id", default=None)
_workflow_type: ContextVar[str | None] = ContextVar("juvera_workflow_type", default=None)
_domain: ContextVar[str | None] = ContextVar("juvera_domain", default=None)
_business_unit: ContextVar[str | None] = ContextVar("juvera_business_unit", default=None)
_user_id: ContextVar[str | None] = ContextVar("juvera_user_id", default=None)
_session_id: ContextVar[str | None] = ContextVar("juvera_session_id", default=None)
_subject_key: ContextVar[str | None] = ContextVar("juvera_subject_key", default=None)
_context_metadata: ContextVar[dict[str, Any] | None] = ContextVar("juvera_context_metadata", default=None)
_context_tags: ContextVar[tuple[str, ...]] = ContextVar("juvera_context_tags", default=())

# Current Juvera span (for nested wrappers).
_current_span: ContextVar[Any] = ContextVar("juvera_current_span", default=None)


def get_work_item_id() -> str | None:
    return _work_item_id.get()


def has_explicit_work_item() -> bool:
    return bool(_work_item_explicit.get())


def set_work_item_id(value: str | None):
    token = _work_item_id.set(value)
    _work_item_explicit.set(bool(value))
    return token


def get_agent_id() -> str | None:
    return _agent_id.get()


def set_agent_id(value: str | None):
    return _agent_id.set(value)


def get_workflow_type() -> str | None:
    return _workflow_type.get()


def get_domain() -> str | None:
    return _domain.get()


def get_business_unit() -> str | None:
    return _business_unit.get()


def get_user_id() -> str | None:
    return _user_id.get()


def get_session_id() -> str | None:
    return _session_id.get()


def get_subject_key() -> str | None:
    return _subject_key.get()


def get_context_metadata() -> dict[str, Any] | None:
    metadata = _context_metadata.get()
    return dict(metadata) if metadata else None


def get_context_tags() -> list[str]:
    return list(_context_tags.get() or ())


def get_context_snapshot() -> dict[str, Any]:
    return {
        "work_item_id": get_work_item_id(),
        "work_item_explicit": has_explicit_work_item(),
        "agent_id": get_agent_id(),
        "workflow_type": get_workflow_type(),
        "domain": get_domain(),
        "business_unit": get_business_unit(),
        "user_id": get_user_id(),
        "session_id": get_session_id(),
        "subject_key": get_subject_key(),
        "metadata": get_context_metadata(),
        "tags": get_context_tags(),
    }


def set_work_item(work_item_id: str, workflow_type: str | None = None) -> None:
    if not isinstance(work_item_id, str) or not work_item_id:
        raise ValueError("work_item_id must be a non-empty string")
    _work_item_id.set(work_item_id)
    _work_item_explicit.set(True)
    _workflow_type.set(workflow_type)


def clear_work_item() -> None:
    _work_item_id.set(None)
    _work_item_explicit.set(False)
    _workflow_type.set(None)


def set_context(
    *,
    user_id: str | None = None,
    session_id: str | None = None,
    subject_key: str | None = None,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | tuple[str, ...] | None = None,
) -> None:
    if user_id is not None:
        _user_id.set(str(user_id))
    if session_id is not None:
        _session_id.set(str(session_id))
    if subject_key is not None:
        _subject_key.set(str(subject_key))
    if metadata is not None:
        _context_metadata.set(dict(metadata))
    if tags is not None:
        _context_tags.set(tuple(str(tag) for tag in tags))


def clear_context() -> None:
    _user_id.set(None)
    _session_id.set(None)
    _subject_key.set(None)
    _context_metadata.set(None)
    _context_tags.set(())


def get_current_span():
    return _current_span.get()


def set_current_span(span):
    return _current_span.set(span)


def clear_current_span():
    _current_span.set(None)


class _ScopedDecorator:
    def _clone(self):
        raise NotImplementedError

    def _enter_scope(self) -> list[tuple[ContextVar[Any], Any]]:
        raise NotImplementedError

    def __enter__(self):
        self._tokens = self._enter_scope()
        return self

    def __exit__(self, exc_type, exc, tb):
        for var, token in reversed(getattr(self, "_tokens", [])):
            var.reset(token)
        self._tokens = []
        return False

    def __call__(self, func: Callable[..., Any]):
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any):
                with self._clone():
                    return await func(*args, **kwargs)

            return async_wrapper

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any):
            with self._clone():
                return func(*args, **kwargs)

        return wrapper


class WorkflowScope(_ScopedDecorator):
    def __init__(
        self,
        *,
        work_item_id: str | None = None,
        workflow_type: str | None = None,
        agent_id: str | None = None,
        domain: str | None = None,
        business_unit: str | None = None,
    ):
        self.work_item_id = work_item_id
        self.workflow_type = workflow_type
        self.agent_id = agent_id
        self.domain = domain
        self.business_unit = business_unit
        self._tokens: list[tuple[ContextVar[Any], Any]] = []

    def _clone(self):
        return WorkflowScope(
            work_item_id=self.work_item_id,
            workflow_type=self.workflow_type,
            agent_id=self.agent_id,
            domain=self.domain,
            business_unit=self.business_unit,
        )

    def _enter_scope(self) -> list[tuple[ContextVar[Any], Any]]:
        tokens: list[tuple[ContextVar[Any], Any]] = []
        if self.work_item_id is not None:
            tokens.append((_work_item_id, _work_item_id.set(str(self.work_item_id))))
            tokens.append((_work_item_explicit, _work_item_explicit.set(bool(self.work_item_id))))
        if self.workflow_type is not None:
            tokens.append((_workflow_type, _workflow_type.set(str(self.workflow_type))))
        if self.agent_id is not None:
            tokens.append((_agent_id, _agent_id.set(str(self.agent_id))))
        if self.domain is not None:
            tokens.append((_domain, _domain.set(str(self.domain))))
        if self.business_unit is not None:
            tokens.append((_business_unit, _business_unit.set(str(self.business_unit))))
        return tokens


class ContextScope(_ScopedDecorator):
    def __init__(
        self,
        *,
        user_id: str | None = None,
        session_id: str | None = None,
        subject_key: str | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | tuple[str, ...] | None = None,
    ):
        self.user_id = user_id
        self.session_id = session_id
        self.subject_key = subject_key
        self.metadata = dict(metadata) if metadata is not None else None
        self.tags = tuple(str(tag) for tag in tags) if tags is not None else None
        self._tokens: list[tuple[ContextVar[Any], Any]] = []

    def _clone(self):
        return ContextScope(
            user_id=self.user_id,
            session_id=self.session_id,
            subject_key=self.subject_key,
            metadata=self.metadata,
            tags=self.tags,
        )

    def _enter_scope(self) -> list[tuple[ContextVar[Any], Any]]:
        tokens: list[tuple[ContextVar[Any], Any]] = []
        if self.user_id is not None:
            tokens.append((_user_id, _user_id.set(str(self.user_id))))
        if self.session_id is not None:
            tokens.append((_session_id, _session_id.set(str(self.session_id))))
        if self.subject_key is not None:
            tokens.append((_subject_key, _subject_key.set(str(self.subject_key))))
        if self.metadata is not None:
            tokens.append((_context_metadata, _context_metadata.set(dict(self.metadata))))
        if self.tags is not None:
            tokens.append((_context_tags, _context_tags.set(tuple(self.tags))))
        return tokens


def workflow(
    *,
    work_item_id: str | None = None,
    workflow_type: str | None = None,
    agent_id: str | None = None,
    domain: str | None = None,
    business_unit: str | None = None,
) -> WorkflowScope:
    return WorkflowScope(
        work_item_id=work_item_id,
        workflow_type=workflow_type,
        agent_id=agent_id,
        domain=domain,
        business_unit=business_unit,
    )


def context(
    *,
    user_id: str | None = None,
    session_id: str | None = None,
    subject_key: str | None = None,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | tuple[str, ...] | None = None,
) -> ContextScope:
    return ContextScope(
        user_id=user_id,
        session_id=session_id,
        subject_key=subject_key,
        metadata=metadata,
        tags=tags,
    )
