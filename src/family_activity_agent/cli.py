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
from groq import APIConnectionError, APITimeoutError, RateLimitError
from langchain_core.tracers.langchain import wait_for_all_tracers
from langgraph.types import Command

from .agent import PROJECT_ROOT, build_family_agent


RUN_ARTIFACTS = (
    "work/event_request.json",
    "work/calendar_plan.json",
    "work/reminder_plan.json",
    "work/weekly_schedule.json",
    "work/assignment_proposal.json",
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
        "recursion_limit": 30,
        "run_name": "family-activity-cli-request",
        "tags": ["family-activity-agent", "cli", "mvp"],
        "metadata": {
            "surface": "cli",
            "model": model or os.getenv(
                "FAMILY_ACTIVITY_MODEL", "openai/gpt-oss-20b"
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
            "Groq's rate limit was reached, so the request could not finish."
            f"{retry} Check the calendar before retrying because an earlier "
            "approved action may already have completed."
        )
    if isinstance(error, APITimeoutError | asyncio.TimeoutError | TimeoutError):
        return (
            "The model request timed out. Check the calendar before retrying "
            "because an earlier approved action may already have completed."
        )
    if isinstance(error, APIConnectionError):
        return "Could not connect to Groq. Check your network and try again."
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


def print_final(result: dict) -> None:
    messages = result.get("messages", [])
    if not messages:
        print(result)
        return
    content = getattr(messages[-1], "content", messages[-1])
    print(content)


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
