from __future__ import annotations
import re
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import ReadableSpan


@dataclass
class PiiMatch:
    pii_type: str
    confidence: str
    span_attribute: str


_PII_PATTERNS: list[tuple[str, str, re.Pattern]] = [
    ("email", "high", re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")),
    ("phone", "medium", re.compile(r"(?<!\w)(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")),
    ("ssn", "high", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("credit_card", "high", re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b")),
    ("api_key", "high", re.compile(r"\b(sk-[a-zA-Z0-9]{20,}|jvr_[a-zA-Z0-9]+|ghp_[a-zA-Z0-9]+)\b")),
]


def scan_span_for_pii(span: ReadableSpan) -> list[PiiMatch]:
    matches: list[PiiMatch] = []
    attrs = span.attributes or {}
    for key, value in attrs.items():
        if not isinstance(value, str):
            continue
        for pii_type, confidence, pattern in _PII_PATTERNS:
            if pattern.search(value):
                matches.append(PiiMatch(pii_type=pii_type, confidence=confidence, span_attribute=key))
    return matches


def warn_pii(span: ReadableSpan, matches: list[PiiMatch]) -> None:
    trace_id = format(span.context.trace_id, "032x") if span.context else "unknown"
    for match in matches:
        print(
            f"\u26a0 PII detected in span attribute '{match.span_attribute}': "
            f"{match.pii_type} (confidence: {match.confidence})\n"
            f"  Span: {span.name} / trace_id: {trace_id}\n"
            f"  Recommendation: review agent output filter before production",
            file=sys.stderr,
        )
