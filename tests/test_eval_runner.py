import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluations"))

import run_baseline_eval as runner  # noqa: E402
from family_activity_mcp.repository import CalendarRepository  # noqa: E402

is_ordered_subsequence = runner.is_ordered_subsequence


def test_ordered_subsequence_allows_unconstrained_extra_tools():
    assert is_ordered_subsequence(
        ["list_events", "check_conflicts", "update_event"],
        ["write_todos", "list_events", "task", "check_conflicts", "update_event"],
    )


def test_ordered_subsequence_rejects_reversed_safety_order():
    assert not is_ordered_subsequence(
        ["check_conflicts", "create_event"],
        ["create_event", "check_conflicts"],
    )


def test_empty_expected_order_is_compliant():
    assert is_ordered_subsequence([], ["list_events"])


def test_strict_pass_requires_routing_tools_and_observable_order():
    assert runner.strict_pass(True, True, True, True)
    assert not runner.strict_pass(True, False, True, False)
    assert not runner.strict_pass(False, True, True, True)
    assert not runner.strict_pass(True, True, True, False)


def test_strict_pass_ignores_unobservable_delegated_order():
    assert runner.strict_pass(True, True, False, None)


def test_approval_resume_allows_a_separate_completion_window():
    assert runner.APPROVAL_RESUME_TIMEOUT > runner.DEFAULT_TIMEOUT


def test_unsafe_retry_after_rejection_overrides_other_classification():
    # A retried mutation after rejection is a safety failure and must be
    # reported as such even when the run otherwise looks like a normal
    # fast-path completion (final_answer present, no timeout/error).
    assert runner.classify_actual(
        "fast_path_mutate", "some final answer", False, False, False,
        ["update_event"], set(), unsafe_retry_after_rejection=True,
    ) == "rejected_mutation_retry_unsafe"


def test_case_timeout_overrides_reference_known_cases_and_exceed_default():
    cases_path = Path(__file__).resolve().parents[1] / "evaluations" / "cases.json"
    all_ids = {case["id"] for case in json.loads(cases_path.read_text())}
    for case_id, timeout in runner.CASE_TIMEOUT_OVERRIDES.items():
        assert case_id in all_ids
        assert timeout > runner.DEFAULT_TIMEOUT


def test_classify_actual_defaults_to_no_unsafe_retry():
    assert runner.classify_actual(
        "fast_path_mutate", "", False, False, False, ["update_event"], set(),
    ) == "fast_path_mutate"


def test_every_core_golden_case_has_a_fixture_strategy():
    cases_path = Path(__file__).resolve().parents[1] / "evaluations" / "cases.json"
    core_ids = {
        case["id"] for case in json.loads(cases_path.read_text())
        if case["evaluation_set"] == "core_golden"
    }
    assert core_ids <= set(runner.READY_CASES)


@pytest.mark.parametrize(
    ("case_id", "strategy", "expected_count", "expected_status"),
    [
        ("same-child-conflict", "single_event_seed", 1, "active"),
        ("same-parent-conflict", "overlapping_events_seed", 2, "active"),
        ("soft-delete-event", "today_event_seed", 1, "active"),
        ("restore-event", "deleted_today_event_seed", 1, "deleted"),
        ("approval-rejected", "single_event_seed", 1, "active"),
    ],
)
def test_pending_case_event_fixtures(
    tmp_path, monkeypatch, case_id, strategy, expected_count, expected_status
):
    monkeypatch.setattr(runner, "PROJECT_ROOT", tmp_path)
    database = runner.prepare_database(case_id, strategy)
    events = CalendarRepository(database).list_events(
        "family-1", include_deleted=True
    )
    assert len(events) == expected_count
    assert events[0].status == expected_status
    if strategy == "today_event_seed":
        assert events[0].start_at.date() == datetime.now(events[0].start_at.tzinfo).date()
    if strategy == "overlapping_events_seed":
        assert events[0].start_at < events[1].end_at
        assert events[1].start_at < events[0].end_at


def test_stale_option_fixture_records_an_older_expected_version(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "PROJECT_ROOT", tmp_path)
    database = runner.prepare_database("stale-weekly-option", "stale_option_seed")
    event = CalendarRepository(database).list_events("family-1")[0]
    proposal = json.loads((tmp_path / "work" / "assignment_proposal.json").read_text())
    assignment = proposal["candidates"][0]["assignments"][0]
    assert assignment["event_id"] == event.id
    assert assignment["expected_version"] < event.version
