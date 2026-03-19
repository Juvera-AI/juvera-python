"""
Example 03: LangChain agent instrumentation.

Assumes `langchain` and `langchain-openai` are installed.
This example shows the pattern — adapt to your chain/agent structure.
"""

import os
import juvera_sdk as j

j.init(
    api_key=os.environ.get("JUVERA_API_KEY", "jvr_demo_key"),
    org_id="org_acme",
    endpoint="local",
    service_name="langchain-agent",
    domain="operations",
)


def run_langchain_agent(user_query: str, work_item_id: str) -> str:
    """
    Wraps a LangChain agent invocation in a Juvera agent_span.

    In production, replace the simulated block with your actual chain:

        from langchain_openai import ChatOpenAI
        from langchain.agents import create_react_agent, AgentExecutor
        # ... set up tools, prompt, agent ...
        result = agent_executor.invoke({"input": user_query})
        return result["output"]
    """
    with j.agent_span(
        agent_id="langchain_agent_01",
        work_item_id=work_item_id,
        workflow_type="document_qa",
    ) as span:
        span.set_model("gpt-4o-mini", provider="openai")

        # Simulated tool calls the chain might make:
        span.add_tool_call("retrieve_documents", status="success")
        span.add_tool_call("rerank_results", status="success")

        answer = f"Simulated LangChain answer for: {user_query}"
        span.set_tokens(input=800, output=250)
        return answer


result = run_langchain_agent("Summarise Q3 incident reports", work_item_id="wi_LC_001")
print(result)

j.record_impact_signal(
    impact_type="throughput_increase",
    value=1.0,
    unit="reports",
    work_item_id="wi_LC_001",
    source_system="jira",
    impact_category="report_automation",
)

j.flush()
