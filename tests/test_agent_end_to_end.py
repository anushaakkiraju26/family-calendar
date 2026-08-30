import asyncio
from uuid import uuid4

from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.types import Command

from family_activity_agent.agent import build_family_agent
from family_activity_agent.cli import pending_requests
from family_activity_mcp.repository import CalendarRepository


class ToolCallingFakeModel(FakeMessagesListChatModel):
    """Deterministic model that accepts the tools bound by Deep Agents."""

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        return self


def invoke(agent, payload, config):
    return asyncio.run(agent.ainvoke(payload, config=config))


def test_read_request_calls_real_mcp_subprocess_without_live_model(tmp_path, monkeypatch):
    database = tmp_path / "agent-read.db"
    monkeypatch.setenv("FAMILY_ACTIVITY_DB", str(database))
    model = ToolCallingFakeModel(responses=[
        AIMessage(content="", tool_calls=[{
            "name": "list_events",
            "args": {"family_id": "family-1"},
            "id": "read-events",
        }]),
        AIMessage(content="No activities are scheduled."),
    ])
    agent = asyncio.run(build_family_agent(model))
    config = {"configurable": {"thread_id": str(uuid4())}}

    result = invoke(
        agent,
        {"messages": [{"role": "user", "content": "Show family-1 activities"}]},
        config,
    )

    assert result["messages"][-1].content == "No activities are scheduled."
    tool_messages = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    assert any(m.name == "list_events" and m.content == "[]" for m in tool_messages)


def test_mutation_requires_approval_then_changes_real_database(tmp_path, monkeypatch):
    database = tmp_path / "agent-write.db"
    monkeypatch.setenv("FAMILY_ACTIVITY_DB", str(database))
    model = ToolCallingFakeModel(responses=[
        AIMessage(content="", tool_calls=[{
            "name": "create_event",
            "args": {
                "family_id": "family-1",
                "title": "Soccer Practice",
                "start_at": "2035-09-01T16:00:00-07:00",
                "end_at": "2035-09-01T17:00:00-07:00",
                "child_id": "leo",
                "idempotency_key": "eval-leo-soccer-2035-09-01",
            },
            "id": "create-soccer",
        }]),
        AIMessage(content="The event was added after approval."),
    ])
    agent = asyncio.run(build_family_agent(model))
    config = {"configurable": {"thread_id": str(uuid4())}}

    interrupted = invoke(
        agent,
        {"messages": [{"role": "user", "content": "Add Leo's soccer practice"}]},
        config,
    )
    requests = pending_requests(interrupted)
    assert [request["name"] for request in requests] == ["create_event"]
    assert CalendarRepository(str(database)).list_events("family-1") == []

    completed = invoke(
        agent,
        Command(resume={"decisions": [{"type": "approve"}]}),
        config,
    )
    events = CalendarRepository(str(database)).list_events("family-1")
    assert [event.title for event in events] == ["Soccer Practice"]
    assert completed["messages"][-1].content == "The event was added after approval."
