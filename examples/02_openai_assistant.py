"""
Example 02: Wrapping an OpenAI chat completion.

Assumes `openai` is installed: pip install openai
Set OPENAI_API_KEY in your environment before running.
"""

import os
import juvera_sdk as j

j.init(
    api_key=os.environ.get("JUVERA_API_KEY", "jvr_demo_key"),
    org_id="org_acme",
    endpoint="local",
    service_name="openai-agent",
    domain="support",
)

def answer_question(question: str, work_item_id: str) -> str:
    with j.agent_span(
        agent_id="openai_agent_01",
        work_item_id=work_item_id,
        workflow_type="qa",
    ) as span:
        span.set_model("gpt-4o", provider="openai")

        # In a real scenario you would call the OpenAI API here:
        # from openai import OpenAI
        # client = OpenAI()
        # response = client.chat.completions.create(
        #     model="gpt-4o",
        #     messages=[{"role": "user", "content": question}],
        # )
        # answer = response.choices[0].message.content
        # span.set_tokens(
        #     input=response.usage.prompt_tokens,
        #     output=response.usage.completion_tokens,
        # )

        # Simulated response for demo:
        answer = f"Simulated answer to: {question}"
        span.set_tokens(input=120, output=60)
        return answer

result = answer_question("What is the return policy?", work_item_id="wi_OA_001")
print(result)

j.record_impact_signal(
    impact_type="time_saved",
    value=300.0,
    unit="seconds",
    work_item_id="wi_OA_001",
    source_system="helpdesk",
)

j.flush()
