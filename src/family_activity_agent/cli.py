from __future__ import annotations

import argparse
import asyncio
import json
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
    "work/outing_proposal.json",
    "work/outing_web_evidence.json",
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


def apply_outing_verification_boundary(
    text: str,
    request: str,
    evidence_urls: set[str] | None = None,
) -> str:
    """Reject unsupported outing claims at the user-output boundary."""
    request_lower = request.lower()
    outing_request = any(term in request_lower for term in (
        "places to visit", "outing", "activities near", "things to do",
        "weekend activities", "holiday activities",
    ))
    if not outing_request or not text:
        return text

    text = re.sub(
        r"(?i)the agent verified[^.\n]*(?:drive|driving)[^.\n]*\.?,?",
        "Drive times were not verified; check them in a current maps app.",
        text,
    )
    text = re.sub(
        r"(?i)fall within a reasonable driving distance",
        "may fit the requested driving range",
        text,
    )
    text = re.sub(
        r"(?i)(?:comfortably reachable|confirmed to be reachable|confirmed within)"
        r"[^.\n]*(?:drive|driving)?",
        "estimated to be nearby; verify the route in a current maps app",
        text,
    )
    text = re.sub(
        r"(?i)that are within (?:roughly |approximately |about )?a?\s*"
        r"45[-‑ ]minute drive of San[  ]Jose",
        "near San Jose, with estimated drive times to verify in a maps app",
        text,
    )
    text = re.sub(
        r"(?i)within (?:roughly |approximately |about )?a?\s*45[-‑ ]minute drive",
        "with estimated drive times that must be verified in a maps app",
        text,
    )
    text = text.replace(
        "that are with estimated drive times that must be verified in a maps app of San Jose",
        "near San Jose, with estimated drive times to verify in a maps app",
    )
    text = re.sub(
        r"(?i)all three are confirmed to be ([^,.]+), family-friendly, and ",
        r"The official pages support that they are \1. They are ",
        text,
    )
    text = re.sub(
        r"(?i)all locations are in San[  ]Jose, so travel time should be "
        r"well within the limit\. ?",
        "All drive times are estimates; verify each route in a maps app. ",
        text,
    )
    text = re.sub(
        r"(?i)(?:the weekend itself is clear|the weekend is clear|"
        r"the closure (?:will be|is) lifted for the weekend)",
        "current closure status must be checked on the operator's alerts page",
        text,
    )

    violations = []
    prohibited_sources = {
        "nomadasaurus.com": "third-party travel blog",
        "bayareakidfun.com": "third-party activity directory",
        "tripadvisor.": "third-party review site",
        "yelp.": "third-party review site",
        "sanjose.org/things-to-do": (
            "tourism roundup rather than an official venue page"
        ),
    }
    lowered_text = text.lower()
    for marker, reason in prohibited_sources.items():
        if marker in lowered_text:
            violations.append(reason)
    if evidence_urls is not None:
        normalized_evidence = {url.rstrip("/") for url in evidence_urls}
        output_urls = {
            url.rstrip("/.,;:>)").rstrip("/")
            for url in re.findall(r"https?://[^\s)\]]+", text)
        }
        ungrounded_urls = output_urls - normalized_evidence
        if ungrounded_urls:
            violations.append(
                "source URLs that were not returned by the outing research tool: "
                + ", ".join(sorted(ungrounded_urls))
            )
        scheduled_claim = re.search(
            r"(?i)\b(?:join|attend)\b[^.\n]*(?:guided|ranger-led|scheduled)"
            r"[^.\n]*(?:walk|tour|program|event)",
            text,
        )
        dated_event_url = any(
            re.search(r"(?i)(?:event|calendar|schedule)", url)
            for url in output_urls
        )
        if scheduled_claim and not dated_event_url:
            violations.append(
                "a scheduled or guided activity without an exact official "
                "event/calendar page for the requested weekend"
            )
    if violations:
        details = "\n".join(
            f"- {violation}" for violation in dict.fromkeys(violations)
        )
        return (
            "Outing research was incomplete, so no recommendations are being "
            "presented as verified. The evidence check rejected the draft for:\n\n"
            f"{details}\n\n"
            "No calendar changes were made. Run the request again; each option "
            "must be supported by its official venue or agency page retrieved "
            "with `you-contents`. Any suggested drive time must be labeled as "
            "an estimate for the parent to verify in a current maps app."
        )

    text = re.sub(
        r"(?i)all options are (?:confirmed|verified) open[^.]*\.",
        "Venue availability and drive times require verification.",
        text,
    )
    note = (
        "Verification note: ‘No calendar conflicts’ only means the proposed "
        "window is free in the stored family calendar. Venue hours, operating "
        "dates, tickets, costs, and drive times must be checked on the linked "
        "venue pages and in a current map before leaving."
    )
    if not re.search(r"https?://", text):
        note += " No source URLs were returned, so this recommendation list is incomplete."
    return f"{text.rstrip()}\n\n{note}"


def print_final(result: dict, request: str = "") -> None:
    text = final_text(result)
    if text:
        evidence_urls = None
        evidence_path = PROJECT_ROOT / "work" / "outing_web_evidence.json"
        if evidence_path.exists():
            try:
                evidence = json.loads(evidence_path.read_text())
                evidence_urls = set(
                    evidence.get("source_urls")
                    or evidence.get("candidate_urls", [])
                )
            except (OSError, ValueError, TypeError):
                evidence_urls = set()
        print(apply_outing_verification_boundary(
            text, request, evidence_urls=evidence_urls
        ))
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

    print_final(result, message)


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
