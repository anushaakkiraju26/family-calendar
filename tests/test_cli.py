import asyncio
import sqlite3

from groq import APIConnectionError, APITimeoutError

from family_activity_agent.cli import (
    RUN_ARTIFACTS,
    clear_run_artifacts,
    format_failure,
    run_config,
    tracing_enabled,
)


def test_timeout_failure_is_actionable_and_does_not_assume_success():
    message = format_failure(APITimeoutError(request=None))
    assert "timed out" in message
    assert "Check the calendar" in message


def test_connection_failure_is_concise():
    message = format_failure(APIConnectionError(request=None))
    assert message == "Could not connect to Groq. Check your network and try again."


def test_database_and_unknown_failures_do_not_claim_success():
    assert "No success is assumed" in format_failure(sqlite3.OperationalError("locked"))
    assert "No success is assumed" in format_failure(RuntimeError("unexpected"))


def test_async_timeout_is_handled():
    assert "timed out" in format_failure(asyncio.TimeoutError())


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
