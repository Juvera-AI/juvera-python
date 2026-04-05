import pytest
import juvera_sdk as j
from juvera_sdk.exporters.mock import MockExporter
import importlib

_ctx = importlib.import_module("juvera_sdk.context")


@pytest.fixture(autouse=True)
def sdk_init(mock_exporter):
    j.init(api_key="jvr_test", org_id="org_test", endpoint="local", _exporter=mock_exporter)
    yield mock_exporter
    j.shutdown()


def test_set_work_item_propagates_to_agent_span(sdk_init):
    exporter = sdk_init
    j.set_work_item("wi_from_middleware", workflow_type="ticket_deflection")
    with j.agent_span(agent_id="agent_01") as span:
        pass
    j.clear_work_item()
    attrs = exporter.last_span().attributes
    assert attrs["juvera.work_item_id"] == "wi_from_middleware"
    assert attrs["juvera.workflow_type"] == "ticket_deflection"


def test_explicit_work_item_id_overrides_context_var(sdk_init):
    exporter = sdk_init
    j.set_work_item("wi_from_context")
    with j.agent_span(agent_id="agent_01", work_item_id="wi_explicit") as span:
        pass
    j.clear_work_item()
    attrs = exporter.last_span().attributes
    assert attrs["juvera.work_item_id"] == "wi_explicit"


def test_explicit_workflow_type_overrides_context_var(sdk_init):
    exporter = sdk_init
    j.set_work_item("wi_001", workflow_type="from_context")
    with j.agent_span(agent_id="agent_01", workflow_type="from_explicit") as span:
        pass
    j.clear_work_item()
    attrs = exporter.last_span().attributes
    assert attrs["juvera.workflow_type"] == "from_explicit"


def test_clear_work_item_resets_both_vars(sdk_init):
    j.set_work_item("wi_001", workflow_type="some_type")
    j.clear_work_item()
    assert _ctx.get_work_item_id() is None
    assert _ctx.get_workflow_type() is None


def test_set_work_item_with_none_raises(sdk_init):
    with pytest.raises(ValueError):
        j.set_work_item(None)


def test_set_work_item_with_empty_string_raises(sdk_init):
    with pytest.raises(ValueError):
        j.set_work_item("")


def test_uuid_generated_when_no_context_var_set(sdk_init):
    exporter = sdk_init
    with j.agent_span(agent_id="agent_01") as span:
        pass
    attrs = exporter.last_span().attributes
    assert attrs.get("juvera.work_item_id") is not None
    assert len(attrs["juvera.work_item_id"]) > 8


def test_workflow_and_context_helpers_propagate_to_agent_span(sdk_init):
    exporter = sdk_init
    with j.context(user_id="u_1", session_id="sess_1", subject_key="customer_1", metadata={"tier": "enterprise"}, tags=["prod"]):
        with j.workflow(work_item_id="wi_ctx", workflow_type="ticket_deflection", agent_id="agent_ctx", domain="support"):
            with j.agent_span(agent_id="agent_ctx") as span:
                span.set_experiment("exp_1", "variant_a", subject_key="customer_1")

    attrs = exporter.last_span().attributes
    assert attrs["juvera.work_item_id"] == "wi_ctx"
    assert attrs["juvera.workflow_type"] == "ticket_deflection"
    assert attrs["juvera.domain"] == "support"
    assert attrs["juvera.user_id"] == "u_1"
    assert attrs["juvera.session_id"] == "sess_1"
    assert attrs["juvera.properties.subject_key"] == "customer_1"
    assert attrs["juvera.instrumentation_readiness"] == "measurement_ready"
