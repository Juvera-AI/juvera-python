"""Local relay for Juvera onboarding and smoke-test capture."""
from __future__ import annotations

import argparse
import json
import socket
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx
from juvera_sdk.costs import estimate_token_cost_usd, resolve_model_pricing

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 4318
DEFAULT_INGEST_ENDPOINT = "http://localhost:8001"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _otel_value(value: Any) -> dict[str, Any]:
    if isinstance(value, bool):
        return {"boolValue": value}
    if isinstance(value, int):
        return {"intValue": value}
    if isinstance(value, float):
        return {"doubleValue": value}
    return {"stringValue": str(value)}


def _attrs_to_dict(attrs: list[dict[str, Any]] | None) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in attrs or []:
        key = item.get("key")
        value = item.get("value") or {}
        if "stringValue" in value:
            result[key] = value["stringValue"]
        elif "intValue" in value:
            result[key] = value["intValue"]
        elif "doubleValue" in value:
            result[key] = value["doubleValue"]
        elif "boolValue" in value:
            result[key] = value["boolValue"]
    return result


def _upsert_attr(attrs: list[dict[str, Any]], key: str, value: Any) -> None:
    for item in attrs:
        if item.get("key") == key:
            item["value"] = _otel_value(value)
            return
    attrs.append({"key": key, "value": _otel_value(value)})


def detect_project_context(cwd: str | None = None) -> dict[str, Any]:
    base = Path(cwd or ".").resolve()
    candidate_files = [
        "pyproject.toml",
        "requirements.txt",
        "requirements-dev.txt",
        "poetry.lock",
        "Pipfile",
    ]
    corpus: list[str] = []
    files_seen: list[str] = []
    for rel_path in candidate_files:
        path = base / rel_path
        if not path.is_file():
            continue
        try:
            corpus.append(path.read_text())
            files_seen.append(rel_path)
        except OSError:
            continue

    joined = "\n".join(corpus).lower()
    indicators = {
        "openai_agents": ("openai-agents", "agents"),
        "langgraph": ("langgraph",),
        "langchain": ("langchain",),
        "crewai": ("crewai",),
        "autogen": ("pyautogen", "autogen"),
        "openai": ("openai",),
        "anthropic": ("anthropic",),
    }
    frameworks = [name for name, tokens in indicators.items() if any(token in joined for token in tokens)]
    return {
        "cwd": str(base),
        "filesScanned": files_seen,
        "frameworks": frameworks,
    }


def _preferred_framework(project_context: dict[str, Any], providers: list[str], frameworks: list[str]) -> str:
    candidates = set(project_context.get("frameworks") or []) | set(providers) | set(frameworks)
    for name in ("openai_agents", "langgraph", "langchain", "crewai", "autogen", "openai", "anthropic"):
        if name in candidates:
            return name
    return "sdk"


def _build_upgrade_plan(
    *,
    project_context: dict[str, Any],
    providers: list[str],
    frameworks: list[str],
    relay_base_url: str = "http://127.0.0.1:4318",
) -> dict[str, Any]:
    framework = _preferred_framework(project_context, providers, frameworks)
    if framework == "openai_agents":
        return {
            "framework": framework,
            "installCommand": 'pip install "juvera-sdk[openai-agents]"',
            "upgradeFrom": "proxy",
            "code": (
                "import juvera_sdk as j\n\n"
                f'j.init(endpoint="{relay_base_url}", debug=False)\n'
                'j.instrument_openai_agents(default_workflow_type="support_ticket_resolution")\n'
            ),
        }
    if framework == "langgraph":
        return {
            "framework": framework,
            "installCommand": 'pip install "juvera-sdk[langgraph]"',
            "upgradeFrom": "proxy",
            "code": (
                "import juvera_sdk as j\n\n"
                f'j.init(endpoint="{relay_base_url}", debug=False)\n'
                "j.instrument_langgraph()\n\n"
                'with j.workflow(work_item_id=ticket_id, workflow_type="support_ticket_resolution", agent_id="support_agent"):\n'
                "    graph.invoke(payload)\n"
            ),
        }
    if framework == "langchain":
        return {
            "framework": framework,
            "installCommand": 'pip install "juvera-sdk[langchain]"',
            "upgradeFrom": "proxy",
            "code": (
                "import juvera_sdk as j\n\n"
                f'j.init(endpoint="{relay_base_url}", debug=False)\n'
                "j.instrument_langchain()\n\n"
                'with j.workflow(work_item_id=ticket_id, workflow_type="support_ticket_resolution", agent_id="support_agent"):\n'
                "    chain.invoke(payload)\n"
            ),
        }
    if framework == "crewai":
        return {
            "framework": framework,
            "installCommand": 'pip install "juvera-sdk[crewai]"',
            "upgradeFrom": "proxy",
            "code": (
                "import juvera_sdk as j\n\n"
                f'j.init(endpoint="{relay_base_url}", debug=False)\n'
                'j.instrument_crewai(default_workflow_type="support_ticket_resolution")\n'
            ),
        }
    if framework == "autogen":
        return {
            "framework": framework,
            "installCommand": 'pip install "juvera-sdk[autogen]"',
            "upgradeFrom": "proxy",
            "code": (
                "import juvera_sdk as j\n\n"
                f'j.init(endpoint="{relay_base_url}", debug=False)\n'
                'j.instrument_autogen(default_workflow_type="support_ticket_resolution")\n'
            ),
        }
    if framework == "anthropic":
        return {
            "framework": framework,
            "installCommand": 'pip install "juvera-sdk[anthropic]"',
            "upgradeFrom": "proxy",
            "code": (
                "import juvera_sdk as j\n"
                "from anthropic import Anthropic\n\n"
                f'j.init(endpoint="{relay_base_url}", debug=False)\n'
                'client = j.wrap_anthropic(Anthropic(), agent_id="support_agent", default_workflow_type="support_ticket_resolution")\n\n'
                'with j.workflow(work_item_id=ticket_id, workflow_type="support_ticket_resolution"):\n'
                "    client.messages.create(model=model, messages=messages)\n"
            ),
        }
    if framework == "openai":
        return {
            "framework": framework,
            "installCommand": 'pip install "juvera-sdk[openai]"',
            "upgradeFrom": "proxy",
            "code": (
                "import juvera_sdk as j\n"
                "from openai import OpenAI\n\n"
                f'j.init(endpoint="{relay_base_url}", debug=False)\n'
                'client = j.wrap_openai(OpenAI(), agent_id="support_agent", default_workflow_type="support_ticket_resolution")\n\n'
                'with j.workflow(work_item_id=ticket_id, workflow_type="support_ticket_resolution"):\n'
                "    client.chat.completions.create(model=model, messages=messages)\n"
            ),
        }
    return {
        "framework": "sdk",
        "installCommand": 'pip install juvera-sdk',
        "upgradeFrom": "proxy",
        "code": (
            "import juvera_sdk as j\n\n"
            f'j.init(endpoint="{relay_base_url}", debug=False)\n'
            'with j.workflow(work_item_id=ticket_id, workflow_type="support_ticket_resolution", agent_id="support_agent"):\n'
            "    ...\n"
        ),
    }


def _collect_cost_health(flat_attrs: list[dict[str, Any]]) -> dict[str, Any]:
    providers = sorted({str(attrs.get("gen_ai.system")).lower() for attrs in flat_attrs if attrs.get("gen_ai.system")})
    models = sorted({str(attrs.get("gen_ai.request.model")).lower() for attrs in flat_attrs if attrs.get("gen_ai.request.model")})
    token_usage_detected = False
    pricing_resolved = False
    cost_computed = False
    total_cost = 0.0
    strategies: set[str] = set()

    for attrs in flat_attrs:
        model = attrs.get("gen_ai.request.model")
        provider = attrs.get("gen_ai.system")
        input_tokens_present = "gen_ai.usage.input_tokens" in attrs or "gen_ai.usage.prompt_tokens" in attrs
        output_tokens_present = "gen_ai.usage.output_tokens" in attrs or "gen_ai.usage.completion_tokens" in attrs
        input_tokens = int(attrs.get("gen_ai.usage.input_tokens") or attrs.get("gen_ai.usage.prompt_tokens") or 0)
        output_tokens = int(attrs.get("gen_ai.usage.output_tokens") or attrs.get("gen_ai.usage.completion_tokens") or 0)
        token_usage_detected = token_usage_detected or input_tokens_present or output_tokens_present
        rates, _, strategy = resolve_model_pricing(model, provider=provider)
        if rates is not None and (provider or model):
            pricing_resolved = True
        if input_tokens or output_tokens:
            estimated_cost, strategy = estimate_token_cost_usd(
                model=model,
                provider=provider,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
            total_cost += estimated_cost
            cost_computed = cost_computed or estimated_cost > 0
        strategies.add(strategy)

    return {
        "providerDetected": bool(providers),
        "modelDetected": bool(models),
        "tokenUsageDetected": token_usage_detected,
        "pricingResolved": pricing_resolved,
        "costComputed": cost_computed,
        "estimatedCostUsd": round(total_cost, 6),
        "pricingStrategies": sorted(strategy for strategy in strategies if strategy),
        "detectedProviders": providers,
        "detectedModels": models,
    }


def inspect_trace_envelope(envelope: dict[str, Any]) -> dict[str, Any]:
    spans = []
    for resource_span in envelope.get("resourceSpans") or []:
        for scope_span in resource_span.get("scopeSpans") or []:
            spans.extend(scope_span.get("spans") or [])
    flat_attrs = [_attrs_to_dict(span.get("attributes") or []) for span in spans]
    has_juvera_attrs = any(any(key.startswith("juvera.") for key in attrs) for attrs in flat_attrs)
    source_mode = "sdk" if has_juvera_attrs else "attach"
    agent_id = any(bool(attrs.get("juvera.agent_id")) for attrs in flat_attrs)
    workflow_type = any(bool(attrs.get("juvera.workflow_type")) for attrs in flat_attrs)
    work_item_id = any(
        bool(attrs.get("juvera.work_item_id")) and not bool(attrs.get("juvera.work_item_auto_generated"))
        for attrs in flat_attrs
    )
    subject_key = any(bool(attrs.get("juvera.properties.subject_key")) for attrs in flat_attrs)
    experiment_tags = any(bool(attrs.get("juvera.properties.experiment_id")) for attrs in flat_attrs)
    cost_health = _collect_cost_health(flat_attrs)
    readiness = "measurement_ready" if agent_id and workflow_type and work_item_id and subject_key and experiment_tags else (
        "attribution_ready" if agent_id and workflow_type and work_item_id else "provisional"
    )
    return {
        "sourceMode": source_mode,
        "instrumentationReadiness": readiness,
        "requiredFields": {
            "agent_id": agent_id,
            "workflow_type": workflow_type,
            "work_item_id": work_item_id,
            "subject_key": subject_key,
            "experiment_tags": experiment_tags,
        },
        **cost_health,
    }


def enrich_trace_envelope(envelope: dict[str, Any], session_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    metadata = inspect_trace_envelope(envelope)
    source_mode = metadata["sourceMode"]
    readiness = metadata["instrumentationReadiness"]
    for resource_span in envelope.get("resourceSpans") or []:
        for scope_span in resource_span.get("scopeSpans") or []:
            for span in scope_span.get("spans") or []:
                attrs = span.setdefault("attributes", [])
                _upsert_attr(attrs, "juvera.capture_source", source_mode)
                _upsert_attr(attrs, "juvera.instrumentation_readiness", readiness)
                _upsert_attr(attrs, "juvera.provisional", readiness == "provisional")
                _upsert_attr(attrs, "juvera.relay_session_id", session_id)
    return envelope, metadata


def build_proxy_trace_envelope(
    *,
    provider: str,
    request_json: dict[str, Any] | None,
    response_json: dict[str, Any] | None,
    duration_ms: float,
    session_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    request_json = request_json or {}
    response_json = response_json or {}

    prompt = ""
    completion = ""
    model = request_json.get("model") or response_json.get("model") or "unknown"
    input_tokens = 0
    output_tokens = 0

    if provider == "openai":
        messages = request_json.get("messages") or []
        prompt = "\n".join(str(message.get("content", "")) for message in messages if isinstance(message, dict)).strip()
        choices = response_json.get("choices") or []
        if choices and isinstance(choices[0], dict):
            message = choices[0].get("message") or {}
            completion = str(message.get("content", "")).strip()
        usage = response_json.get("usage") or {}
        input_tokens = int(usage.get("prompt_tokens") or 0)
        output_tokens = int(usage.get("completion_tokens") or 0)
    elif provider == "anthropic":
        messages = request_json.get("messages") or []
        prompt = "\n".join(str(message.get("content", "")) for message in messages if isinstance(message, dict)).strip()
        content = response_json.get("content") or []
        completion = "\n".join(str(item.get("text", "")) for item in content if isinstance(item, dict)).strip()
        usage = response_json.get("usage") or {}
        input_tokens = int(usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)
    estimated_cost_usd, pricing_strategy = estimate_token_cost_usd(
        model=model,
        provider=provider,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )

    work_item_id = str(uuid.uuid4())
    start_ns = time.time_ns()
    end_ns = start_ns + int(duration_ms * 1_000_000)
    envelope = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": _otel_value("juvera-local-relay")},
                        {"key": "juvera.sdk_version", "value": _otel_value("relay")},
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "juvera-local-relay"},
                        "spans": [
                            {
                                "traceId": uuid.uuid4().hex,
                                "spanId": uuid.uuid4().hex[:16],
                                "name": "agent.run",
                                "startTimeUnixNano": str(start_ns),
                                "endTimeUnixNano": str(end_ns),
                                "attributes": [
                                    {"key": "juvera.agent_id", "value": _otel_value("local_proxy_capture")},
                                    {"key": "juvera.workflow_type", "value": _otel_value("llm_proxy_test")},
                                    {"key": "juvera.domain", "value": _otel_value("custom")},
                                    {"key": "juvera.work_item_id", "value": _otel_value(work_item_id)},
                                    {"key": "juvera.capture_source", "value": _otel_value("proxy")},
                                    {"key": "juvera.instrumentation_readiness", "value": _otel_value("provisional")},
                                    {"key": "juvera.provisional", "value": _otel_value(True)},
                                    {"key": "juvera.relay_session_id", "value": _otel_value(session_id)},
                                    {"key": "gen_ai.system", "value": _otel_value(provider)},
                                    {"key": "gen_ai.request.model", "value": _otel_value(model)},
                                    {"key": "gen_ai.prompt", "value": _otel_value(prompt or "[captured via local relay]")},
                                    {"key": "gen_ai.completion", "value": _otel_value(completion or "[provider response captured via local relay]")},
                                    {"key": "gen_ai.usage.input_tokens", "value": _otel_value(input_tokens)},
                                    {"key": "gen_ai.usage.output_tokens", "value": _otel_value(output_tokens)},
                                ],
                            }
                        ],
                    }
                ],
            }
        ]
    }
    return envelope, {
        "sourceMode": "proxy",
        "instrumentationReadiness": "provisional",
        "requiredFields": {
            "agent_id": False,
            "workflow_type": False,
            "work_item_id": False,
            "subject_key": False,
            "experiment_tags": False,
        },
        "providerDetected": bool(provider),
        "modelDetected": model != "unknown",
        "tokenUsageDetected": bool(input_tokens or output_tokens),
        "pricingResolved": pricing_strategy != "missing",
        "costComputed": estimated_cost_usd > 0,
        "estimatedCostUsd": estimated_cost_usd,
        "pricingStrategies": [pricing_strategy],
        "detectedProviders": [provider],
        "detectedModels": [model] if model != "unknown" else [],
    }


@dataclass
class RelayRuntimeState:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: str = field(default_factory=_now_iso)
    last_activity_at: str | None = None
    proxy_traffic_detected: bool = False
    sdk_spans_detected: bool = False
    detected_providers: set[str] = field(default_factory=set)
    detected_frameworks: set[str] = field(default_factory=set)
    traces_forwarded: int = 0
    impacts_forwarded: int = 0
    proxy_captures: int = 0
    last_error: str | None = None
    last_validation: dict[str, Any] = field(default_factory=dict)
    project_context: dict[str, Any] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            detected_frameworks = sorted(set(self.detected_frameworks) | set(self.project_context.get("frameworks") or []))
            suggested_upgrade = _build_upgrade_plan(
                project_context=self.project_context,
                providers=sorted(self.detected_providers),
                frameworks=detected_frameworks,
            )
            return {
                "status": "online",
                "sessionId": self.session_id,
                "startedAt": self.started_at,
                "lastActivityAt": self.last_activity_at,
                "proxyTrafficDetected": self.proxy_traffic_detected,
                "sdkSpansDetected": self.sdk_spans_detected,
                "detectedProviders": sorted(self.detected_providers),
                "detectedFrameworks": detected_frameworks,
                "stats": {
                    "tracesForwarded": self.traces_forwarded,
                    "impactsForwarded": self.impacts_forwarded,
                    "proxyCaptures": self.proxy_captures,
                },
                "lastValidation": self.last_validation,
                "projectContext": self.project_context,
                "suggestedUpgrade": suggested_upgrade,
                "lastError": self.last_error,
            }

    def record_trace(self, metadata: dict[str, Any]) -> None:
        with self.lock:
            self.last_activity_at = _now_iso()
            self.traces_forwarded += 1
            if metadata.get("sourceMode") == "proxy":
                self.proxy_traffic_detected = True
                self.proxy_captures += 1
            else:
                self.sdk_spans_detected = True
                self.detected_frameworks.add(metadata.get("sourceMode") or "sdk")
            for provider in metadata.get("detectedProviders") or []:
                self.detected_providers.add(str(provider))
            self.last_validation = metadata

    def record_provider(self, provider: str, metadata: dict[str, Any]) -> None:
        with self.lock:
            self.last_activity_at = _now_iso()
            self.proxy_traffic_detected = True
            self.proxy_captures += 1
            self.detected_providers.add(provider)
            self.detected_frameworks.add(provider)
            self.last_validation = metadata

    def record_impact(self) -> None:
        with self.lock:
            self.last_activity_at = _now_iso()
            self.impacts_forwarded += 1

    def record_error(self, message: str) -> None:
        with self.lock:
            self.last_error = message


class RelayConfig:
    def __init__(self, host: str, port: int, ingest_endpoint: str, api_key: str | None, org_id: str | None):
        self.host = host
        self.port = port
        self.ingest_endpoint = ingest_endpoint.rstrip("/")
        self.api_key = api_key
        self.org_id = org_id
        self.state = RelayRuntimeState()
        self.state.project_context = detect_project_context()


def _copy_response_headers(source: httpx.Response, handler: BaseHTTPRequestHandler) -> None:
    for key, value in source.headers.items():
        lower = key.lower()
        if lower in {"content-length", "transfer-encoding", "connection", "content-encoding"}:
            continue
        handler.send_header(key, value)


def _send_json(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "*")
    handler.end_headers()
    handler.wfile.write(body)


def _read_json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any] | None:
    length = int(handler.headers.get("Content-Length", "0") or 0)
    raw = handler.rfile.read(length) if length else b"{}"
    if not raw:
        return {}
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return None


def _forward_to_ingest(config: RelayConfig, path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    if not config.api_key:
        return 202, {"accepted": False, "detail": "Relay captured traffic locally, but JUVERA_API_KEY is not set so nothing was forwarded."}
    response = httpx.post(
        f"{config.ingest_endpoint}{path}",
        json=payload,
        headers={"X-API-Key": config.api_key, "Content-Type": "application/json"},
        timeout=10.0,
    )
    response.raise_for_status()
    try:
        return response.status_code, response.json()
    except Exception:
        return response.status_code, {"accepted": True}


def _proxy_request(handler: BaseHTTPRequestHandler, provider: str, target_base: str, config: RelayConfig) -> None:
    split = urlsplit(handler.path)
    prefix = f"/proxy/{provider}/"
    target_path = split.path[len(prefix):]
    target_url = f"{target_base.rstrip('/')}/{target_path.lstrip('/')}"
    if split.query:
        target_url = f"{target_url}?{split.query}"

    body = handler.rfile.read(int(handler.headers.get("Content-Length", "0") or 0))
    forward_headers = {
        key: value
        for key, value in handler.headers.items()
        if key.lower() not in {"host", "content-length", "connection"}
    }

    started = time.perf_counter()
    with httpx.Client(timeout=30.0) as client:
        response = client.request(handler.command, target_url, content=body, headers=forward_headers)
    duration_ms = (time.perf_counter() - started) * 1000

    request_json = None
    response_json = None
    try:
        request_json = json.loads(body.decode("utf-8")) if body else {}
    except Exception:
        request_json = {}
    try:
        response_json = response.json()
    except Exception:
        response_json = {}

    try:
        envelope, metadata = build_proxy_trace_envelope(
            provider=provider,
            request_json=request_json,
            response_json=response_json,
            duration_ms=duration_ms,
            session_id=config.state.session_id,
        )
        _forward_to_ingest(config, "/v1/traces", envelope)
        config.state.record_provider(provider, metadata)
    except Exception as exc:
        config.state.record_error(f"proxy capture failed: {exc}")

    handler.send_response(response.status_code)
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "*")
    _copy_response_headers(response, handler)
    payload = response.content
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def build_handler(config: RelayConfig):
    class RelayHandler(BaseHTTPRequestHandler):
        server_version = "JuveraLocalRelay/0.1"

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/health":
                _send_json(self, 200, {"status": "ok"})
                return
            if self.path == "/status":
                _send_json(self, 200, config.state.snapshot())
                return
            _send_json(self, 404, {"detail": "Not found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path == "/v1/traces":
                payload = _read_json_body(self)
                if payload is None:
                    _send_json(self, 400, {"detail": "Invalid JSON"})
                    return
                try:
                    enriched, metadata = enrich_trace_envelope(payload, config.state.session_id)
                    status, response_body = _forward_to_ingest(config, "/v1/traces", enriched)
                    config.state.record_trace(metadata)
                    _send_json(self, status, response_body)
                except Exception as exc:
                    config.state.record_error(str(exc))
                    _send_json(self, 502, {"detail": f"Failed to forward traces: {exc}"})
                return

            if self.path == "/v1/impact-signals":
                payload = _read_json_body(self)
                if payload is None:
                    _send_json(self, 400, {"detail": "Invalid JSON"})
                    return
                try:
                    status, response_body = _forward_to_ingest(config, "/v1/impact-signals", payload)
                    config.state.record_impact()
                    _send_json(self, status, response_body)
                except Exception as exc:
                    config.state.record_error(str(exc))
                    _send_json(self, 502, {"detail": f"Failed to forward impact signals: {exc}"})
                return

            if self.path.startswith("/proxy/openai/"):
                _proxy_request(self, "openai", "https://api.openai.com", config)
                return

            if self.path.startswith("/proxy/anthropic/"):
                _proxy_request(self, "anthropic", "https://api.anthropic.com", config)
                return

            _send_json(self, 404, {"detail": "Not found"})

    return RelayHandler


def run_listen(args: argparse.Namespace) -> int:
    config = RelayConfig(
        host=args.host,
        port=args.port,
        ingest_endpoint=args.ingest_endpoint,
        api_key=args.api_key,
        org_id=args.org_id,
    )
    server = ThreadingHTTPServer((args.host, args.port), build_handler(config))
    print(f"[juvera] Local Relay listening on http://{args.host}:{args.port}")
    print(f"[juvera] Status endpoint: http://{args.host}:{args.port}/status")
    print(f"[juvera] Proxy OpenAI via http://{args.host}:{args.port}/proxy/openai/v1")
    print(f"[juvera] Proxy Anthropic via http://{args.host}:{args.port}/proxy/anthropic/v1")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[juvera] Local Relay stopped.")
    finally:
        server.server_close()
    return 0


def _probe_port(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((DEFAULT_HOST, port)) == 0


def run_doctor(args: argparse.Namespace) -> int:
    base_url = args.base_url.rstrip("/")
    try:
        response = httpx.get(f"{base_url}/status", timeout=2.0)
        response.raise_for_status()
        payload = response.json()
        print("[juvera] Local Relay is online.")
        print(json.dumps(payload, indent=2))
    except Exception as exc:
        print(f"[juvera] Local Relay is offline: {exc}")
    if args.scan_ports:
        common_ports = [3000, 5000, 8000, 8080]
        open_ports = [port for port in common_ports if _probe_port(port)]
        if open_ports:
            print(f"[juvera] Detected local dev ports: {', '.join(str(port) for port in open_ports)}")
        else:
            print("[juvera] No approved common dev ports detected.")
    return 0


def run_validate(args: argparse.Namespace) -> int:
    base_url = args.base_url.rstrip("/")
    try:
        response = httpx.get(f"{base_url}/status", timeout=2.0)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        print(f"[juvera] Validation failed: relay unavailable ({exc})")
        return 1

    checks = payload.get("lastValidation", {}).get("requiredFields") or {}
    if not checks:
        print("[juvera] No trace or proxy capture detected yet.")
        return 1

    blocking = []
    for field, present in checks.items():
        status = "ok" if present else "missing"
        print(f"[juvera] {field}: {status}")
        if field in {"agent_id", "workflow_type", "work_item_id"} and not present:
            blocking.append(field)

    last_validation = payload.get("lastValidation", {})
    print(f"[juvera] providerDetected: {'ok' if last_validation.get('providerDetected') else 'missing'}")
    print(f"[juvera] modelDetected: {'ok' if last_validation.get('modelDetected') else 'missing'}")
    print(f"[juvera] tokenUsageDetected: {'ok' if last_validation.get('tokenUsageDetected') else 'missing'}")
    print(f"[juvera] pricingResolved: {'ok' if last_validation.get('pricingResolved') else 'missing'}")
    print(f"[juvera] costComputed: {'ok' if last_validation.get('costComputed') else 'missing'}")
    if last_validation.get("estimatedCostUsd") is not None:
        print(f"[juvera] estimatedCostUsd: {last_validation.get('estimatedCostUsd')}")

    readiness = last_validation.get("instrumentationReadiness")
    print(f"[juvera] instrumentationReadiness: {readiness}")
    suggested_upgrade = payload.get("suggestedUpgrade") or {}
    if suggested_upgrade.get("framework"):
        print(f"[juvera] recommendedUpgrade: {suggested_upgrade['framework']}")
    if last_validation.get("tokenUsageDetected") and not last_validation.get("costComputed"):
        blocking.append("cost_health")
    return 1 if blocking else 0


def run_patch(args: argparse.Namespace) -> int:
    project_context = detect_project_context(getattr(args, "cwd", None))
    providers: list[str] = []
    frameworks: list[str] = list(project_context.get("frameworks") or [])
    base_url = getattr(args, "base_url", f"http://{DEFAULT_HOST}:{DEFAULT_PORT}").rstrip("/")
    try:
        response = httpx.get(f"{base_url}/status", timeout=2.0)
        response.raise_for_status()
        payload = response.json()
        providers = payload.get("detectedProviders") or []
        frameworks = sorted(set(frameworks) | set(payload.get("detectedFrameworks") or []))
    except Exception:
        payload = {}

    plan = _build_upgrade_plan(
        project_context=project_context,
        providers=providers,
        frameworks=frameworks,
        relay_base_url=base_url,
    )
    print(f"[juvera] recommended framework: {plan['framework']}")
    print(f"[juvera] install: {plan['installCommand']}")
    print("[juvera] snippet:")
    print(plan["code"])
    if payload.get("lastValidation"):
        print("[juvera] relay status included in recommendation.")
    return 0
