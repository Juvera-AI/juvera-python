"""Juvera MCP Server — local tools for AI agent instrumentation."""
from __future__ import annotations

import json
import re
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from juvera_sdk.roi import WORKFLOW_BASELINES

mcp = FastMCP("juvera")


# ── Tool 1: ROI Estimation ──────────────────────────────────────────────────

@mcp.tool()
def juvera_roi(workflow_type: str, agent_cost_usd: float = 0.0) -> dict:
    """Get ROI estimate for a workflow type.

    Returns baseline cost, estimated savings, and time saved
    based on industry-standard workflow baselines.

    Args:
        workflow_type: One of ticket_deflection, lead_qualification,
            document_review, data_extraction, code_review,
            compliance_check, content_generation
        agent_cost_usd: Cost of the agent run in USD (default 0.0)
    """
    baseline = WORKFLOW_BASELINES.get(workflow_type)
    if baseline is None:
        return {
            "error": f"Unknown workflow_type: {workflow_type}",
            "known_types": list(WORKFLOW_BASELINES.keys()),
        }
    cost = baseline["human_cost_usd"]
    time_min = baseline["human_time_minutes"]
    savings = cost - agent_cost_usd
    time_saved = time_min * (savings / cost) if cost > 0 else 0.0
    return {
        "workflow_type": workflow_type,
        "baseline_cost_usd": cost,
        "baseline_time_minutes": time_min,
        "agent_cost_usd": round(agent_cost_usd, 4),
        "estimated_savings_usd": round(savings, 2),
        "time_saved_minutes": round(time_saved, 1),
    }


# ── Tool 2: Validation ──────────────────────────────────────────────────────

_INIT_PATTERN = re.compile(r"j(?:uvera_sdk)?\.init\s*\(")
_SPAN_PATTERN = re.compile(r"with\s+j(?:uvera_sdk)?\.agent_span\s*\(")
_FLUSH_PATTERN = re.compile(r"j(?:uvera_sdk)?\.flush\s*\(")
_SHUTDOWN_PATTERN = re.compile(r"j(?:uvera_sdk)?\.shutdown\s*\(")
_SET_MODEL_PATTERN = re.compile(r"\.set_model\s*\(")
_SET_TOKENS_PATTERN = re.compile(r"\.set_tokens\s*\(")
_WORKFLOW_TYPE_PATTERN = re.compile(r"workflow_type\s*=")


@mcp.tool()
def juvera_validate(file_path: str) -> dict:
    """Validate Juvera SDK instrumentation in a Python file.

    Checks for common issues: missing init(), unclosed spans,
    missing flush()/shutdown(), missing model/token tracking.

    Args:
        file_path: Absolute path to the Python file to validate
    """
    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}
    if not path.suffix == ".py":
        return {"error": "Only Python files are supported"}

    code = path.read_text()
    issues: list[dict[str, str]] = []

    has_juvera_import = "juvera_sdk" in code or "import juvera" in code
    if not has_juvera_import:
        return {"status": "no_instrumentation", "issues": [], "message": "No Juvera SDK usage detected"}

    if not _INIT_PATTERN.search(code):
        issues.append({"severity": "error", "message": "Missing j.init() call — SDK must be initialized before use"})

    if not _SPAN_PATTERN.search(code):
        issues.append({"severity": "error", "message": "Missing agent_span() — no spans are being created"})

    if not _FLUSH_PATTERN.search(code):
        issues.append({"severity": "warning", "message": "Missing j.flush() — spans may not be exported before process exit"})

    if not _SHUTDOWN_PATTERN.search(code):
        issues.append({"severity": "warning", "message": "Missing j.shutdown() — resources may not be released cleanly"})

    if _SPAN_PATTERN.search(code):
        if not _SET_MODEL_PATTERN.search(code):
            issues.append({"severity": "info", "message": "No span.set_model() found — model tracking recommended"})
        if not _SET_TOKENS_PATTERN.search(code):
            issues.append({"severity": "info", "message": "No span.set_tokens() found — token tracking recommended for cost analysis"})
        if not _WORKFLOW_TYPE_PATTERN.search(code):
            issues.append({"severity": "info", "message": "No workflow_type set — required for ROI estimation"})

    status = "pass" if not any(i["severity"] == "error" for i in issues) else "fail"
    return {"status": status, "issues": issues, "file": file_path}


# ── Tool 3: Framework Detection + Suggestions ───────────────────────────────

FRAMEWORK_PATTERNS: list[tuple[str, re.Pattern, str | None]] = [
    ("openai",     re.compile(r"from\s+openai\s+import|import\s+openai"),           "openai"),
    ("anthropic",  re.compile(r"from\s+anthropic\s+import|import\s+anthropic"),      "anthropic"),
    ("langchain",  re.compile(r"from\s+langchain"),                                  "langchain"),
    ("crewai",     re.compile(r"from\s+crewai"),                                     "crewai"),
    ("llamaindex", re.compile(r"from\s+llama_index"),                                "llamaindex"),
    ("fastapi",    re.compile(r"from\s+fastapi\s+import|import\s+fastapi"),          None),
    ("flask",      re.compile(r"from\s+flask\s+import|import\s+flask"),              None),
    ("raw_http",   re.compile(r"requests\.post\s*\(|httpx\.(post|AsyncClient)"),     None),
]

WORKFLOW_HINTS: dict[str, str] = {
    "support": "ticket_deflection",
    "ticket": "ticket_deflection",
    "customer": "ticket_deflection",
    "sales": "lead_qualification",
    "lead": "lead_qualification",
    "legal": "document_review",
    "review": "code_review",
    "code": "code_review",
    "compliance": "compliance_check",
    "content": "content_generation",
    "extract": "data_extraction",
}


def _detect_frameworks(code: str) -> list[str]:
    """Return list of detected framework names."""
    return [name for name, pattern, _ in FRAMEWORK_PATTERNS if pattern.search(code)]


def _guess_workflow_type(code: str, file_path: str) -> str | None:
    """Guess workflow type from code content and file name."""
    text = (code + " " + file_path).lower()
    for keyword, wf_type in WORKFLOW_HINTS.items():
        if keyword in text:
            return wf_type
    return None


def _tier1_snippet(framework: str, workflow_type: str | None) -> str:
    """Return Tier 1 (minimal) instrumentation snippet."""
    wf = f'"{workflow_type}"' if workflow_type else '"ticket_deflection"  # adjust to your workflow'
    return f'''import os
import juvera_sdk as j

j.init(
    api_key=os.environ.get("JUVERA_API_KEY", "jvr_local"),
    org_id=os.environ.get("JUVERA_ORG_ID", "org_local"),
    endpoint="local",
    debug=True,
)

# Wrap your agent logic in an agent_span
with j.agent_span(agent_id="my_agent", workflow_type={wf}) as span:
    span.set_model("gpt-4o", provider="openai")  # adjust model/provider
    span.set_tokens(input=0, output=0)  # fill from response.usage

j.flush()
j.shutdown()'''


def _tier2_snippet() -> str:
    """Return Tier 2 additions."""
    return '''    # Tier 2: Prompt/completion capture + tool tracking
    span.set_prompt(user_message)
    span.set_completion(response_text)
    span.add_tool_call("tool_name", status="success", duration_ms=45)'''


def _tier3_snippet() -> str:
    """Return Tier 3 additions."""
    return '''    # Tier 3: Full observability
    span.add_context_source("knowledge_base", doc_type="pdf", token_count=800)
    j.record_event("guardrail_check", status="success", properties={"rule": "pii_filter"})
    roi = j.estimate_roi(agent_cost_usd=0.002)  # workflow_type inferred from active span

    # Error handling
    try:
        # ... agent logic ...
        pass
    except Exception as e:
        span.set_error(e)
        j.record_handoff(reason="error", reviewer_role="engineer")
        raise

    # Business impact (after confirmed outcome)
    j.record_impact_signal(
        impact_type="cost_reduction",
        value=18.50,
        impact_category="ticket_deflection",
        source_system="your_system",
    )'''


@mcp.tool()
def juvera_suggest(file_path: str) -> dict:
    """Analyze a Python file and suggest Juvera SDK instrumentation.

    Detects AI frameworks, suggests a workflow type, and returns
    code snippets for three progressive tiers of instrumentation.

    Args:
        file_path: Absolute path to the Python file to analyze
    """
    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    code = path.read_text()
    frameworks = _detect_frameworks(code)
    workflow_type = _guess_workflow_type(code, file_path)
    already_instrumented = "juvera_sdk" in code or "import juvera" in code

    return {
        "file": file_path,
        "detected_frameworks": frameworks,
        "suggested_workflow_type": workflow_type,
        "already_instrumented": already_instrumented,
        "tiers": {
            "minimal": {
                "description": "init + agent_span + model + tokens + flush + shutdown",
                "snippet": _tier1_snippet(frameworks[0] if frameworks else "openai", workflow_type),
            },
            "standard": {
                "description": "+ prompt/completion capture + tool call tracking",
                "snippet": _tier2_snippet(),
            },
            "full": {
                "description": "+ events, ROI, context sources, handoffs, error handling, impact signals",
                "snippet": _tier3_snippet(),
            },
        },
    }


# ── Tool 4: Trace Parsing ───────────────────────────────────────────────────

_DEBUG_SPAN_PATTERN = re.compile(
    r"\[juvera-debug\]\s+SPAN\s+name='([^']+)'\s+trace_id=(\w+)\s+agent_id=(\S+)\s+work_item_id=(\S+)\s+attrs=(\{.+\})"
)
_DEBUG_SIGNAL_PATTERN = re.compile(r"\[juvera-debug\]\s+IMPACT_SIGNAL\s+(\{.+\})")


def _parse_debug_log(content: str) -> dict:
    """Parse juvera-debug output into structured summary."""
    spans: list[dict] = []
    signals: list[dict] = []

    for line in content.splitlines():
        span_match = _DEBUG_SPAN_PATTERN.search(line)
        if span_match:
            name, trace_id, agent_id, work_item_id, attrs_json = span_match.groups()
            try:
                attrs = json.loads(attrs_json)
            except json.JSONDecodeError:
                attrs = {}
            spans.append({
                "name": name,
                "trace_id": trace_id,
                "agent_id": agent_id,
                "work_item_id": work_item_id,
                "model": attrs.get("gen_ai.request.model"),
                "input_tokens": attrs.get("gen_ai.usage.input_tokens"),
                "output_tokens": attrs.get("gen_ai.usage.output_tokens"),
                "workflow_type": attrs.get("juvera.workflow_type"),
                "has_prompt": "gen_ai.prompt" in attrs,
                "has_completion": "gen_ai.completion" in attrs,
            })

        signal_match = _DEBUG_SIGNAL_PATTERN.search(line)
        if signal_match:
            try:
                signals.append(json.loads(signal_match.group(1)))
            except json.JSONDecodeError:
                pass

    total_input = sum(s.get("input_tokens") or 0 for s in spans)
    total_output = sum(s.get("output_tokens") or 0 for s in spans)

    return {
        "span_count": len(spans),
        "signal_count": len(signals),
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "spans": spans,
        "signals": signals,
    }


@mcp.tool()
def juvera_traces(log_file_path: str, agent_id: str | None = None, work_item_id: str | None = None) -> dict:
    """Read and summarize Juvera debug traces from a log file.

    The Juvera SDK in debug/local mode writes trace data to stdout.
    Pipe your agent output to a file to use this tool:
        python my_agent.py 2>&1 | tee juvera-debug.log

    Args:
        log_file_path: Absolute path to the log file containing [juvera-debug] output
        agent_id: Optional filter — only show spans from this agent
        work_item_id: Optional filter — only show spans for this work item
    """
    path = Path(log_file_path)
    if not path.exists():
        return {"error": f"Log file not found: {log_file_path}"}

    content = path.read_text()
    result = _parse_debug_log(content)

    if agent_id:
        result["spans"] = [s for s in result["spans"] if s["agent_id"] == agent_id]
    if work_item_id:
        result["spans"] = [s for s in result["spans"] if s["work_item_id"] == work_item_id]
    result["span_count"] = len(result["spans"])

    return result


if __name__ == "__main__":
    mcp.run(transport="stdio")
