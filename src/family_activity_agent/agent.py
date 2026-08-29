from __future__ import annotations

import os
import sys
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StoreBackend
from langchain_groq import ChatGroq
from langchain_core.tools import StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from .prompts import (
    CALENDAR_PROMPT,
    CONFLICT_PROMPT,
    COORDINATOR_PROMPT,
    INTAKE_PROMPT,
    REMINDER_PROMPT,
    SCHEDULE_REVIEWER_PROMPT,
    WEEKLY_PLANNER_PROMPT,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MUTATING_TOOLS = {
    "create_event",
    "update_event",
    "delete_event",
    "restore_event",
    "schedule_reminder",
    "schedule_day_of_reminders",
    "cancel_reminders",
}


def mcp_connection() -> dict[str, dict[str, Any]]:
    """Launch the local MCP server as a managed stdio subprocess."""
    env = {
        "FAMILY_ACTIVITY_DB": os.getenv(
            "FAMILY_ACTIVITY_DB",
            str(PROJECT_ROOT / "data" / "family_activity.db"),
        )
    }
    return {
        "family_activity": {
            "transport": "stdio",
            "command": sys.executable,
            "args": ["-m", "family_activity_mcp.server", "--transport", "stdio"],
            "env": env,
        }
    }


def select_tools(tools: list[Any], *names: str) -> list[Any]:
    by_name = {tool.name: tool for tool in tools}
    missing = set(names) - set(by_name)
    if missing:
        raise RuntimeError(f"MCP server is missing tools: {sorted(missing)}")
    return [by_name[name] for name in names]


def stringify_tool_result(result: Any) -> str:
    """Flatten LangChain MCP content blocks for Groq tool-message compatibility."""
    if isinstance(result, str):
        return result
    if isinstance(result, list):
        text_parts = [
            block.get("text", "")
            for block in result
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        if text_parts:
            return "\n".join(text_parts)
    return json.dumps(result, default=str)


def groq_compatible_tool(tool: Any) -> StructuredTool:
    """Preserve an MCP tool schema while returning plain string content."""
    async def invoke_tool(**arguments: Any) -> str:
        result = await tool.ainvoke(arguments)
        return stringify_tool_result(result)

    return StructuredTool.from_function(
        coroutine=invoke_tool,
        name=tool.name,
        description=tool.description or tool.name,
        args_schema=tool.args_schema,
    )


async def build_family_agent(model: Any | None = None):
    """Load MCP tools and construct the Family Coordinator Deep Agent."""
    client = MultiServerMCPClient(mcp_connection())
    discovered_tools = await client.get_tools()
    tools = [groq_compatible_tool(tool) for tool in discovered_tools]

    calendar_tools = select_tools(
        tools, "create_event", "list_events", "update_event",
        "delete_event", "restore_event", "check_conflicts",
        "list_school_events", "check_school_conflicts",
    )
    conflict_tools = select_tools(
        tools, "check_conflicts", "check_school_conflicts"
    )
    weekly_planning_tools = select_tools(
        tools, "list_events", "check_conflicts", "list_school_events",
        "check_school_conflicts",
    )
    reminder_tools = select_tools(
        tools, "list_events", "list_reminders", "schedule_reminder",
        "schedule_day_of_reminders", "cancel_reminders"
    )

    skills_path = "/skills/"
    store = InMemoryStore()
    backend = CompositeBackend(
        default=FilesystemBackend(root_dir=str(PROJECT_ROOT), virtual_mode=True),
        routes={"/memories/": StoreBackend(namespace=lambda context: ("family",))},
    )
    interrupt_on = {name: True for name in MUTATING_TOOLS}

    pacific_time = datetime.now(ZoneInfo("America/Los_Angeles")).isoformat()
    intake_prompt = (
        f"Current Pacific date and time: {pacific_time}. "
        "Use this only to resolve relative dates such as today and tomorrow.\n\n"
        f"{INTAKE_PROMPT}"
    )
    coordinator_prompt = (
        f"Current Pacific date and time: {pacific_time}. "
        "Family timezone: America/Los_Angeles. "
        "School hours: Monday-Friday, 9:00 AM-3:00 PM.\n\n"
        f"{COORDINATOR_PROMPT}"
    )

    subagents = [
        {
            "name": "intake-agent",
            "description": "Normalizes every parent request and identifies ambiguity. Use first.",
            "system_prompt": intake_prompt,
            "tools": [],
        },
        {
            "name": "calendar-agent",
            "description": "Reads and changes events through the family calendar MCP tools.",
            "system_prompt": CALENDAR_PROMPT,
            "tools": calendar_tools,
            "skills": [skills_path],
            "interrupt_on": interrupt_on,
        },
        {
            "name": "conflict-agent",
            "description": (
                "Checks a proposed time for child, parent, school-hour, or "
                "dated school-calendar conflicts."
            ),
            "system_prompt": CONFLICT_PROMPT,
            "tools": conflict_tools,
        },
        {
            "name": "weekly-planner",
            "description": (
                "Builds or revises a complete weekly family plan using family "
                "events, Reed Elementary dates, conflicts, and parent assignments."
            ),
            "system_prompt": WEEKLY_PLANNER_PROMPT,
            "tools": weekly_planning_tools,
            "skills": [skills_path],
        },
        {
            "name": "schedule-reviewer",
            "description": (
                "Independently reviews a weekly plan and requires revision when "
                "conflicts, missing details, or unsafe times remain."
            ),
            "system_prompt": SCHEDULE_REVIEWER_PROMPT,
            "tools": [],
            "skills": [skills_path],
        },
        {
            "name": "reminder-agent",
            "description": "Plans, schedules, and cancels event reminders.",
            "system_prompt": REMINDER_PROMPT,
            "tools": reminder_tools,
            "skills": [skills_path],
            "interrupt_on": interrupt_on,
        },
    ]

    if model is not None and not isinstance(model, str):
        chat_model = model
    else:
        model_name = model or os.getenv(
            "FAMILY_ACTIVITY_MODEL",
            "openai/gpt-oss-20b",
        )
        if model_name.startswith("groq:"):
            model_name = model_name.removeprefix("groq:")
        chat_model = ChatGroq(
            model=model_name,
            temperature=0,
            timeout=30,
            max_retries=int(os.getenv("FAMILY_ACTIVITY_MAX_RETRIES", "2")),
        )

    agent = create_deep_agent(
        name="family-coordinator",
        model=chat_model,
        system_prompt=coordinator_prompt,
        tools=tools,
        subagents=subagents,
        skills=[skills_path],
        backend=backend,
        store=store,
        checkpointer=InMemorySaver(),
        interrupt_on=interrupt_on,
    )
    return agent
