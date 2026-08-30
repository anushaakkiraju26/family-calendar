from __future__ import annotations

import argparse
import asyncio
import os
import re
import sqlite3
import traceback
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from openai import APIConnectionError, APITimeoutError, RateLimitError
from langchain_core.tracers.langchain import wait_for_all_tracers
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.types import Command
from langgraph.errors import GraphRecursionError

from .agent import PROJECT_ROOT, build_family_agent


RUN_ARTIFACTS = (
    "work/event_request.json",
    "work/calendar_plan.json",
    "work/reminder_plan.json",
    "work/weekly_schedule.json",
    "work/assignment_proposal.json",
    "work/transportation_plan.json",
    "reviews/conflict_report.json",
    "reviews/weekly_schedule_review.json",
    "final/completed_action.json",
)


def clear_run_artifacts(project_root: Path = PROJECT_ROOT) -> None:
    """Remove only ephemeral Deep Agent files from the previous CLI run."""
    for relative_path in RUN_ARTIFACTS:
        (project_root / relative_path).unlink(missing_ok=True)


def tracing_enabled() -> bool:
    return os.getenv("LANGSMITH_TRACING", "false").lower() in {
        "1", "true", "yes", "on",
    }


def run_config(thread_id: str, model: str | None) -> dict:
    """Attach non-sensitive labels inherited by LangSmith child runs."""
    return {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 60,
        "run_name": "family-activity-cli-request",
        "tags": ["family-activity-agent", "cli", "mvp"],
        "metadata": {
            "surface": "cli",
            "model": model or os.getenv(
                "FAMILY_ACTIVITY_MODEL", "nvidia/Nemotron-3-Nano-Omni"
            ),
            "reminder_mode": "draft-only",
        },
    }


def format_failure(error: Exception) -> str:
    """Return a safe, actionable CLI message without leaking a traceback."""
    if isinstance(error, RateLimitError):
        match = re.search(
            r"Please try again in ([0-9.]+(?:ms|s|m|h)(?:[0-9.]+s)?)",
            str(error),
            flags=re.IGNORECASE,
        )
        retry = f" Retry after approximately {match.group(1)}." if match else ""
        return (
            "Nebius's rate limit was reached, so the request could not finish."
            f"{retry} Check the calendar before retrying because an earlier "
            "approved action may already have completed."
        )
    if isinstance(error, APITimeoutError | asyncio.TimeoutError | TimeoutError):
        return (
            "The model request timed out. Check the calendar before retrying "
            "because an earlier approved action may already have completed."
        )
    if isinstance(error, APIConnectionError):
        return "Could not connect to Nebius. Check your network and try again."
    if isinstance(error, GraphRecursionError):
        return (
            "The planning workflow reached its safety step limit before producing "
            "a reviewed plan. No calendar changes were made."
        )
    if isinstance(error, sqlite3.Error):
        return "The calendar database could not complete the request. No success is assumed."
    if "mcp" in type(error).__module__.lower() or "mcp" in str(error).lower():
        return "The calendar tool server failed. No success is assumed; please retry."
    return (
        "The request failed unexpectedly. No success is assumed. "
        "Run again with --debug to see technical details."
    )


def pending_requests(result: dict) -> list[dict]:
    requests = []
    for interrupt in result.get("__interrupt__", []):
        value = interrupt.value
        if isinstance(value, dict) and "action_requests" in value:
            requests.extend(value["action_requests"])
        elif isinstance(value, list):
            requests.extend(value)
        else:
            requests.append(value)
    return requests


def message_text(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "\n".join(part for part in parts if part.strip()).strip()
    return str(content).strip() if content is not None else ""


def final_text(result: dict) -> str:
    messages = result.get("messages", [])
    if not messages:
        return message_text(result)
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            text = message_text(message.content)
            if text:
                return text
    for message in reversed(messages):
        if isinstance(message, ToolMessage):
            text = message_text(message.content)
            if text:
                return text
    return ""


def print_final(result: dict) -> None:
    text = final_text(result)
    if text:
        print(text)
    else:
        print(
            "The agent stopped without producing a final response. "
            "No calendar changes are assumed; please retry with --debug."
        )


async def run(message: str, thread_id: str, model: str | None) -> None:
    clear_run_artifacts()
    agent = await build_family_agent(model)
    config = run_config(thread_id, model)
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": message}]},
        config=config,
    )

    while "__interrupt__" in result:
        requests = pending_requests(result)
        decisions = []
        for request in requests:
            print("\nPending approval:")
            print(request)
            answer = input("Approve this action? [y/N]: ").strip().lower()
            if answer in {"y", "yes"}:
                decisions.append({"type": "approve"})
            else:
                feedback = input("Reason or requested change: ").strip()
                decisions.append({
                    "type": "reject",
                    "message": feedback or "The parent rejected this action.",
                })
        result = await agent.ainvoke(
            Command(resume={"decisions": decisions}),
            config=config,
        )

    print_final(result)


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Family Coordinator Deep Agent")
    parser.add_argument("message", help="Parent request in natural language")
    parser.add_argument("--thread-id", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument(
        "--debug", action="store_true", help="Show a traceback when a request fails"
    )
    args = parser.parse_args()
    try:
        asyncio.run(run(args.message, args.thread_id or str(uuid4()), args.model))
    except KeyboardInterrupt:
        print("\nRequest cancelled. A pending action was not approved.")
        raise SystemExit(130) from None
    except EOFError:
        print("\nInput ended before approval. The pending action was not approved.")
        raise SystemExit(1) from None
    except Exception as error:
        print(f"\n❌ {format_failure(error)}")
        if args.debug:
            traceback.print_exc()
        raise SystemExit(1) from None
    finally:
        if tracing_enabled():
            try:
                wait_for_all_tracers()
            except Exception:
                if args.debug:
                    traceback.print_exc()


if __name__ == "__main__":
    main()
