import asyncio
import sqlite3

from openai import APIConnectionError, APITimeoutError
from langgraph.errors import GraphRecursionError

from family_activity_agent.cli import (
    RUN_ARTIFACTS,
    apply_outing_verification_boundary,
    clear_run_artifacts,
    format_failure,
    final_text,
    run_config,
    tracing_enabled,
)
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


def test_timeout_failure_is_actionable_and_does_not_assume_success():
    message = format_failure(APITimeoutError(request=None))
    assert "timed out" in message
    assert "Check the calendar" in message


def test_connection_failure_is_concise():
    message = format_failure(APIConnectionError(request=None))
    assert message == "Could not connect to Nebius. Check your network and try again."


def test_database_and_unknown_failures_do_not_claim_success():
    assert "No success is assumed" in format_failure(sqlite3.OperationalError("locked"))
    assert "No success is assumed" in format_failure(RuntimeError("unexpected"))


def test_async_timeout_is_handled():
    assert "timed out" in format_failure(asyncio.TimeoutError())


def test_recursion_limit_failure_does_not_claim_success():
    message = format_failure(GraphRecursionError("limit"))
    assert "safety step limit" in message
    assert "No calendar changes" in message


def test_final_text_skips_empty_trailing_assistant_message():
    result = {"messages": [
        HumanMessage(content="request"),
        AIMessage(content="Reviewed plan"),
        AIMessage(content=""),
    ]}
    assert final_text(result) == "Reviewed plan"


def test_final_text_falls_back_to_substantive_tool_result():
    result = {"messages": [
        HumanMessage(content="request"),
        ToolMessage(content="Reviewer requires revision", tool_call_id="call-1"),
        AIMessage(content=""),
    ]}
    assert final_text(result) == "Reviewer requires revision"


def test_outing_output_qualifies_calendar_and_venue_claims():
    text = apply_outing_verification_boundary(
        "All options are confirmed open and within 45 minutes. "
        "Source: https://example.org/venue",
        "Find activities near San Jose this weekend",
    )
    assert "confirmed open" not in text
    assert "No calendar conflicts" in text
    assert "must be checked" in text
    assert "recommendation list is incomplete" not in text


def test_outing_output_without_sources_is_marked_incomplete():
    text = apply_outing_verification_boundary(
        "Try the local museum.",
        "Find places to visit this weekend",
    )
    assert "No source URLs were returned" in text


def test_non_outing_output_is_unchanged():
    text = "No activities are scheduled."
    assert apply_outing_verification_boundary(
        text, "Show today's activities"
    ) == text


def test_outing_boundary_rejects_aggregator_and_unmapped_drive_time():
    text = apply_outing_verification_boundary(
        "Children's museum has IMAX screenings and is a 5-10 min drive. "
        "Source: https://www.sanjose.org/things-to-do/kids-family",
        "Find family activities near San Jose this weekend",
    )

    assert "Outing research was incomplete" in text
    assert "tourism roundup" in text
    assert "Children's museum" not in text


def test_outing_boundary_does_not_blanket_reject_imax_on_official_page():
    text = apply_outing_verification_boundary(
        "The Tech Interactive has an IMAX Dome Theater. "
        "https://www.thetech.org/explore/imax-dome-theater/",
        "Find science activities near San Jose this weekend",
    )

    assert "Outing research was incomplete" not in text
    assert "IMAX Dome Theater" in text


def test_outing_boundary_allows_suggested_drive_time_with_verification_note():
    text = apply_outing_verification_boundary(
        "The Tech is a 5-10 min drive. "
        "https://www.thetech.org/",
        "Find science activities near San Jose this weekend",
    )

    assert "Outing research was incomplete" not in text
    assert "5-10 min drive" in text
    assert "drive times must be checked" in text


def test_outing_boundary_removes_false_drive_verification_claim():
    text = apply_outing_verification_boundary(
        "These fall within a reasonable driving distance; the agent verified "
        "they're each ≤45 min drive. https://www.thetech.org/",
        "Find science activities near San Jose this weekend",
    )

    assert "agent verified" not in text
    assert "fall within a reasonable" not in text
    assert "Drive times were not verified" in text


def test_outing_boundary_removes_comfortably_reachable_claim():
    text = apply_outing_verification_boundary(
        "All three are confirmed to be science-focused, family-friendly, and "
        "comfortably reachable within a 45-minute drive. "
        "https://www.thetech.org/",
        "Find science activities near San Jose this weekend",
    )

    assert "comfortably reachable" not in text
    assert "confirmed to be" not in text
    assert "verify the route" in text


def test_outing_boundary_rejects_url_not_returned_by_research_tool():
    text = apply_outing_verification_boundary(
        "Children's museum: https://www.sjcdm.org",
        "Find science activities near San Jose this weekend",
        evidence_urls={"https://www.cdm.org/"},
    )

    assert "Outing research was incomplete" in text
    assert "not returned by the outing research tool" in text
    assert "sjcdm.org" in text


def test_outing_boundary_accepts_exact_research_url():
    text = apply_outing_verification_boundary(
        "Children's museum: https://www.cdm.org/",
        "Find science activities near San Jose this weekend",
        evidence_urls={"https://www.cdm.org/"},
    )

    assert "Outing research was incomplete" not in text
    assert "https://www.cdm.org/" in text


def test_outing_boundary_rewrites_drive_phrase_grammatically():
    text = apply_outing_verification_boundary(
        "Here are activities that are within roughly a 45-minute drive of "
        "San Jose. https://www.thetech.org/",
        "Find science activities near San Jose this weekend",
    )

    assert "that are with" not in text
    assert "near San Jose, with estimated drive times" in text


def test_outing_boundary_removes_city_implies_drive_limit_claim():
    text = apply_outing_verification_boundary(
        "All locations are in San Jose, so travel time should be well within "
        "the limit. https://www.thetech.org/",
        "Find science activities near San Jose this weekend",
    )

    assert "well within" not in text
    assert "verify each route" in text


def test_outing_boundary_rejects_undated_guided_program():
    text = apply_outing_verification_boundary(
        "Join a free guided nature walk this weekend. "
        "https://www.openspaceauthority.org/",
        "Find outdoor activities near San Jose this weekend",
        evidence_urls={"https://www.openspaceauthority.org/"},
    )

    assert "Outing research was incomplete" in text
    assert "without an exact official event/calendar page" in text


def test_outing_boundary_does_not_claim_closure_is_clear():
    text = apply_outing_verification_boundary(
        "The park had a Friday closure, but the weekend itself is clear. "
        "https://www.sanjoseca.gov/parks",
        "Find outdoor activities near San Jose this weekend",
    )

    assert "weekend itself is clear" not in text
    assert "current closure status must be checked" in text


def test_outing_boundary_allows_official_source_without_drive_claim():
    text = apply_outing_verification_boundary(
        "Alum Rock Park — trails and picnic areas. "
        "https://www.sanjoseca.gov/Home/Components/FacilityDirectory/FacilityDirectory/2088/2028",
        "Find outdoor activities near San Jose this weekend",
    )

    assert "Outing research was incomplete" not in text
    assert "Alum Rock Park" in text
    assert "Verification note:" in text


def test_clear_run_artifacts_removes_only_known_ephemeral_files(tmp_path):
    assert "work/weekly_schedule.json" in RUN_ARTIFACTS
    assert "reviews/weekly_schedule_review.json" in RUN_ARTIFACTS
    for relative_path in RUN_ARTIFACTS:
        artifact = tmp_path / relative_path
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("stale")
    database = tmp_path / "data" / "family_activity.db"
    database.parent.mkdir(parents=True)
    database.write_text("persistent")

    clear_run_artifacts(tmp_path)

    assert all(not (tmp_path / path).exists() for path in RUN_ARTIFACTS)
    assert database.read_text() == "persistent"


def test_langsmith_run_config_has_safe_course_labels(monkeypatch):
    monkeypatch.setenv("FAMILY_ACTIVITY_MODEL", "test-model")
    config = run_config("thread-secret", None)
    assert config["run_name"] == "family-activity-cli-request"
    assert config["recursion_limit"] == 60
    assert "family-activity-agent" in config["tags"]
    assert config["metadata"] == {
        "surface": "cli",
        "model": "test-model",
        "reminder_mode": "draft-only",
    }
    assert "thread-secret" not in str(config["metadata"])


def test_langsmith_tracing_is_opt_in(monkeypatch):
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    assert tracing_enabled() is False
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    assert tracing_enabled() is True
