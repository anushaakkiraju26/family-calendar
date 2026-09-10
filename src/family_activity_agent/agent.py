from __future__ import annotations

import os
import sys
import json
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StoreBackend
from langchain_core.tools import StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from .prompts import (
    CALENDAR_PROMPT,
    CONFLICT_PROMPT,
    COORDINATOR_PROMPT,
    INTAKE_PROMPT,
    OUTING_PROMPT,
    REMINDER_PROMPT,
    SCHEDULE_REVIEWER_PROMPT,
    TRANSPORTATION_PROMPT,
    WEEKLY_PLANNER_PROMPT,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAN_JOSE_OFFICIAL_OUTING_DOMAINS = [
    "thetech.org",
    "cdm.org",
    "happyhollow.org",
    "sanjoseca.gov",
    "parks.sccgov.org",
    "fws.gov",
    "openspace.org",
    "historysanjose.org",
]
MUTATING_TOOLS = {
    "create_event",
    "update_event",
    "delete_event",
    "restore_event",
    "schedule_reminder",
    "schedule_day_of_reminders",
    "cancel_reminders",
}


def canonical_outing_url(url: str) -> str:
    """Collapse search-engine variants of the same official destination page."""
    parts = urlsplit(url.replace("&amp;", "&"))
    query = urlencode([
        (key, value) for key, value in parse_qsl(parts.query)
        if key.lower() not in {"amp", "utm_campaign", "utm_content", "utm_medium",
                               "utm_source", "utm_term"}
    ])
    return urlunsplit((
        parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), query, ""
    ))


def mcp_connection() -> dict[str, dict[str, Any]]:
    """Configure the local family server and optional hosted You.com server."""
    env = {
        "FAMILY_ACTIVITY_DB": os.getenv(
            "FAMILY_ACTIVITY_DB",
            str(PROJECT_ROOT / "data" / "family_activity.db"),
        ),
    }
    connections = {
        "family_activity": {
            "transport": "stdio",
            "command": sys.executable,
            "args": ["-m", "family_activity_mcp.server", "--transport", "stdio"],
            "env": env,
        }
    }
    ydc_api_key = os.getenv("YDC_API_KEY", "").strip()
    if ydc_api_key:
        connections["you_com"] = {
            "transport": "streamable_http",
            "url": os.getenv(
                "YDC_MCP_URL",
                "https://api.you.com/mcp?tools=you-search,you-contents,"
                "you-research,you-answer,you-finance,you-balance,you-discover",
            ),
            "headers": {"Authorization": f"Bearer {ydc_api_key}"},
        }
    return connections


def select_tools(tools: list[Any], *names: str) -> list[Any]:
    by_name = {tool.name: tool for tool in tools}
    missing = set(names) - set(by_name)
    if missing:
        raise RuntimeError(f"MCP server is missing tools: {sorted(missing)}")
    return [by_name[name] for name in names]


def stringify_tool_result(result: Any) -> str:
    """Flatten LangChain MCP content blocks for model tool-message compatibility."""
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


def model_compatible_tool(tool: Any) -> StructuredTool:
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


def official_outing_research_tool(search_tool: Any, contents_tool: Any) -> StructuredTool:
    """Combine You.com discovery and page extraction into one reliable call."""
    async def research_official_outings(query: str, count: int = 8) -> str:
        search_arguments = {
            "count": max(3, min(count, 12)),
            "country": "US",
            "safesearch": "strict",
        }
        search_queries = [query]
        if "san jose" in query.lower():
            search_queries = [
                f"{query} official visitor information",
                "San Jose official science museum nature center family visit",
                "San Jose official parks hiking trails family visit",
            ]
            search_arguments["include_domains"] = SAN_JOSE_OFFICIAL_OUTING_DOMAINS
        else:
            search_arguments["exclude_domains"] = [
                "nomadasaurus.com",
                "bayareakidfun.com",
                "tripadvisor.com",
                "yelp.com",
                "sanjose.org",
            ]
        search_texts = []
        results = []
        for search_query in search_queries:
            search_result = await search_tool.ainvoke({
                **search_arguments, "query": search_query
            })
            search_text = stringify_tool_result(search_result)
            search_texts.append(search_text)
            try:
                payload = json.loads(search_text)
                results.extend(payload.get("results", {}).get("web", []))
            except (TypeError, ValueError):
                continue

        urls = []
        for result in results:
            url = result.get("url") if isinstance(result, dict) else None
            candidate_text = " ".join(str(result.get(field, "")) for field in (
                "url", "title", "description"
            )).lower() if isinstance(result, dict) else ""
            excluded_program = any(marker in candidate_text for marker in (
                "camp", "field trip", "field-trip", "field_trip",
                "school program", "presentation program",
            ))
            if (
                isinstance(url, str)
                and url.startswith(("http://", "https://"))
                and not excluded_program
            ):
                urls.append(canonical_outing_url(url))
        urls = list(dict.fromkeys(urls))[:8]
        if not urls:
            return json.dumps({
                "status": "incomplete",
                "reason": "Search returned no candidate URLs for page extraction.",
                "search": search_texts,
            })

        contents_result = await contents_tool.ainvoke({
            "urls": urls,
            "formats": ["markdown", "metadata"],
            "crawl_timeout": 20,
            "max_age": 86400,
        })
        contents_text = stringify_tool_result(contents_result)
        linked_urls = {
            url.rstrip("/.,;:>)").rstrip("/")
            for url in re.findall(r"https?://[^\s)\]]+", contents_text)
        }
        source_urls = sorted({
            *(url.rstrip("/") for url in urls),
            *linked_urls,
        })
        evidence_path = PROJECT_ROOT / "work" / "outing_web_evidence.json"
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(json.dumps({
            "queries": search_queries,
            "candidate_urls": urls,
            "source_urls": source_urls,
        }, indent=2))
        return json.dumps({
            "status": "research_complete",
            "candidate_urls": urls,
            "search": search_texts,
            "page_contents": contents_text,
            "evidence_rule": (
                "Recommend only venue/operator/agency pages whose extracted "
                "content directly supports the stated facts."
            ),
        })

    return StructuredTool.from_function(
        coroutine=research_official_outings,
        name="research_official_outings",
        description=(
            "Search for family outing candidates and retrieve their page contents "
            "in one call. Use this instead of calling you-search directly. Input "
            "a concise 3-6 word query containing the city plus attraction types "
            "such as museum, park, zoo, or nature center. Exclude camps, schools, "
            "and classes unless the request specifically asks for programs."
        ),
    )


def coordinated_outing_research_tool(
    list_events_tool: Any,
    list_school_events_tool: Any,
    search_tool: Any,
    contents_tool: Any,
) -> StructuredTool:
    """Check calendars and retrieve official outing evidence in one call."""
    web_research = official_outing_research_tool(search_tool, contents_tool)

    async def research_family_outings(
        family_id: str,
        start_date: str,
        end_date: str,
        query: str,
        count: int = 8,
    ) -> str:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        if end < start:
            raise ValueError("end_date must be on or after start_date")
        start_at = datetime.combine(
            start, datetime.min.time(), ZoneInfo("America/Los_Angeles")
        )
        end_at = datetime.combine(
            end + timedelta(days=1), datetime.min.time(),
            ZoneInfo("America/Los_Angeles")
        )
        family_events = await list_events_tool.ainvoke({
            "family_id": family_id,
            "start_at": start_at.isoformat(),
            "end_at": end_at.isoformat(),
        })
        school_events = await list_school_events_tool.ainvoke({
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        })
        research = await web_research.ainvoke({"query": query, "count": count})
        return json.dumps({
            "status": "calendar_and_research_complete",
            "family_id": family_id,
            "date_range": {"start": start_date, "end": end_date},
            "family_events": stringify_tool_result(family_events),
            "school_events": stringify_tool_result(school_events),
            "outing_research": stringify_tool_result(research),
        })

    return StructuredTool.from_function(
        coroutine=research_family_outings,
        name="research_family_outings",
        description=(
            "Required one-call outing workflow: list family events, list school "
            "events, then search and extract official visitor-attraction pages. "
            "Provide family_id, inclusive YYYY-MM-DD start_date/end_date, and a "
            "concise city/activity query. This tool never changes the calendar."
        ),
    )


def weekend_ranges(reference_date: date) -> tuple[tuple[date, date], tuple[date, date]]:
    """Return deterministic this-weekend and next-weekend Saturday/Sunday pairs."""
    if reference_date.weekday() == 5:
        this_saturday = reference_date
    elif reference_date.weekday() == 6:
        this_saturday = reference_date - timedelta(days=1)
    else:
        this_saturday = reference_date + timedelta(
            days=(5 - reference_date.weekday())
        )
    this_weekend = (this_saturday, this_saturday + timedelta(days=1))
    next_weekend = (
        this_saturday + timedelta(days=7),
        this_saturday + timedelta(days=8),
    )
    return this_weekend, next_weekend


async def build_family_agent(model: Any | None = None):
    """Load MCP tools and construct the Family Coordinator Deep Agent."""
    client = MultiServerMCPClient(mcp_connection())
    discovered_tools = await client.get_tools()
    tools = [model_compatible_tool(tool) for tool in discovered_tools]
    raw_tools = {tool.name: tool for tool in discovered_tools}
    hosted_you_tool_names = {
        "you-search", "you-contents", "you-research", "you-answer",
        "you-finance", "you-balance", "you-discover",
    }
    coordinator_tools = [
        tool for tool in tools if tool.name not in hosted_you_tool_names
    ]

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
    transportation_tools = select_tools(
        tools, "list_parent_availability", "check_parent_availability",
        "check_transportation_conflicts", "generate_schedule_candidates",
        "review_schedule_candidate",
    )
    reminder_tools = select_tools(
        tools, "list_events", "list_reminders", "schedule_reminder",
        "schedule_day_of_reminders", "cancel_reminders"
    )
    outing_tools = select_tools(
        tools, "list_events", "list_school_events", "check_outing_time_window"
    )
    if "you-search" in raw_tools and "you-contents" in raw_tools:
        outing_research = coordinated_outing_research_tool(
            raw_tools["list_events"], raw_tools["list_school_events"],
            raw_tools["you-search"], raw_tools["you-contents"]
        )
        outing_tools.append(outing_research)
        coordinator_tools.append(outing_research)

    skills_path = "/skills/"
    store = InMemoryStore()
    backend = CompositeBackend(
        default=FilesystemBackend(root_dir=str(PROJECT_ROOT), virtual_mode=True),
        routes={"/memories/": StoreBackend(namespace=lambda context: ("family",))},
    )
    interrupt_on = {name: True for name in MUTATING_TOOLS}

    pacific_now = datetime.now(ZoneInfo("America/Los_Angeles"))
    pacific_time = pacific_now.isoformat()
    this_weekend, next_weekend = weekend_ranges(pacific_now.date())
    weekend_context = (
        f"For this run, this weekend is {this_weekend[0].isoformat()} through "
        f"{this_weekend[1].isoformat()}, and next weekend is "
        f"{next_weekend[0].isoformat()} through {next_weekend[1].isoformat()}. "
    )
    intake_prompt = (
        f"Current Pacific date and time: {pacific_time}. "
        "Use this only to resolve relative dates such as today and tomorrow.\n\n"
        f"{INTAKE_PROMPT}"
    )
    outing_prompt = (
        f"Current Pacific date and time: {pacific_time}. "
        f"{weekend_context}"
        "Use these exact ranges for relative weekend requests.\n\n"
        f"{OUTING_PROMPT}"
    )
    if not any(tool.name == "research_family_outings" for tool in outing_tools):
        outing_prompt += (
            "\n\nYou.com MCP tools are unavailable in this process. Explain that "
            "YDC_API_KEY must be configured locally in .env; never ask the "
            "parent to paste a key and never pretend that live search ran."
        )
    coordinator_prompt = (
        f"Current Pacific date and time: {pacific_time}. "
        f"{weekend_context}"
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
                "events, Maple Grove Elementary dates, conflicts, and parent assignments."
            ),
            "system_prompt": WEEKLY_PLANNER_PROMPT,
            "tools": weekly_planning_tools,
            "skills": [skills_path],
        },
        {
            "name": "transportation-agent",
            "description": (
                "Generates and ranks parent assignments, pickup/drop-off coverage, "
                "availability checks, and travel-feasible weekly candidates."
            ),
            "system_prompt": TRANSPORTATION_PROMPT,
            "tools": transportation_tools,
            "skills": [skills_path],
        },
        {
            "name": "schedule-reviewer",
            "description": (
                "Independently reviews a weekly plan and requires revision when "
                "conflicts, missing details, or unsafe times remain."
            ),
            "system_prompt": SCHEDULE_REVIEWER_PROMPT,
            "tools": select_tools(tools, "review_schedule_candidate"),
            "skills": [skills_path],
        },
        {
            "name": "family-outing-agent",
            "description": (
                "Finds and ranks current family-friendly places for weekends, "
                "long weekends, and school breaks after checking free time."
            ),
            "system_prompt": outing_prompt,
            "tools": outing_tools,
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
            "nvidia/Nemotron-3-Nano-Omni",
        )
        if model_name.startswith("nebius:"):
            model_name = model_name.removeprefix("nebius:")
        chat_model = ChatOpenAI(
            model=model_name,
            api_key=os.getenv("NEBIUS_API_KEY"),
            base_url=os.getenv(
                "NEBIUS_BASE_URL",
                "https://api.tokenfactory.us-central1.nebius.com/v1/",
            ),
            temperature=0,
            timeout=60,
            max_retries=int(os.getenv("FAMILY_ACTIVITY_MAX_RETRIES", "2")),
        )

    agent = create_deep_agent(
        name="family-coordinator",
        model=chat_model,
        system_prompt=coordinator_prompt,
        tools=coordinator_tools,
        subagents=subagents,
        skills=[skills_path],
        backend=backend,
        store=store,
        checkpointer=InMemorySaver(),
        interrupt_on=interrupt_on,
    )
    return agent
