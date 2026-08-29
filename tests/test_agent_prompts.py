from family_activity_agent.prompts import (
    CALENDAR_PROMPT,
    CONFLICT_PROMPT,
    COORDINATOR_PROMPT,
    INTAKE_PROMPT,
    REMINDER_PROMPT,
    SCHEDULE_REVIEWER_PROMPT,
    WEEKLY_PLANNER_PROMPT,
)


def test_file_writing_prompts_include_required_tool_arguments():
    for prompt in (
        INTAKE_PROMPT,
        CALENDAR_PROMPT,
        CONFLICT_PROMPT,
        REMINDER_PROMPT,
        WEEKLY_PLANNER_PROMPT,
        SCHEDULE_REVIEWER_PROMPT,
    ):
        assert "file_path" in prompt
        assert "content" in prompt


def test_coordinator_has_family_time_defaults():
    assert "America/Los_Angeles" in COORDINATOR_PROMPT
    assert "9:00 AM to 3:00 PM" in COORDINATOR_PROMPT
    assert "Vikram is unavailable" in COORDINATOR_PROMPT
    assert "9:30 AM-4:00 PM" in COORDINATOR_PROMPT


def test_coordinator_requires_deep_weekly_workflow_and_review_loop():
    assert "DEEP WEEKLY WORKFLOW" in COORDINATOR_PROMPT
    assert "weekly-planner" in COORDINATOR_PROMPT
    assert "schedule-reviewer" in COORDINATOR_PROMPT
    assert "revision_required" in COORDINATOR_PROMPT
    assert "grouped set" in COORDINATOR_PROMPT


def test_weekly_planner_and_reviewer_use_school_calendar():
    assert "list_school_events" in WEEKLY_PLANNER_PROMPT
    assert "check_school_conflicts" in WEEKLY_PLANNER_PROMPT
    assert "Never send YYYY-MM-DD to list_events" in WEEKLY_PLANNER_PROMPT
    assert "/work/weekly_schedule.json" in WEEKLY_PLANNER_PROMPT
    assert "/reviews/weekly_schedule_review.json" in SCHEDULE_REVIEWER_PROMPT
    assert "same-child overlaps" in SCHEDULE_REVIEWER_PROMPT
    assert "Vikram assigned" in SCHEDULE_REVIEWER_PROMPT
