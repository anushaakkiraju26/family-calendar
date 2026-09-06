from family_activity_agent.prompts import (
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


def test_file_writing_prompts_include_required_tool_arguments():
    for prompt in (
        INTAKE_PROMPT,
        CALENDAR_PROMPT,
        CONFLICT_PROMPT,
        REMINDER_PROMPT,
        WEEKLY_PLANNER_PROMPT,
        SCHEDULE_REVIEWER_PROMPT,
        TRANSPORTATION_PROMPT,
        OUTING_PROMPT,
    ):
        assert "file_path" in prompt
        assert "content" in prompt


def test_coordinator_has_family_time_defaults():
    assert "America/Los_Angeles" in COORDINATOR_PROMPT
    assert "9:00 AM to 3:00 PM" in COORDINATOR_PROMPT
    assert "Vikram is unavailable" in COORDINATOR_PROMPT
    assert "9:30 AM-4:00 PM" in COORDINATOR_PROMPT


def test_outing_workflow_requires_sources_and_calendar_checks():
    assert "OUTING WORKFLOW" in COORDINATOR_PROMPT
    assert "family-outing-agent" in COORDINATOR_PROMPT
    assert "list_events" in OUTING_PROMPT
    assert "list_school_events" in OUTING_PROMPT
    assert "check_outing_time_window" in OUTING_PROMPT
    assert "Call research_family_outings exactly once" in OUTING_PROMPT
    assert "list_events, list_school_events, you-search" in OUTING_PROMPT
    assert "you-search" in OUTING_PROMPT
    assert "you-contents" in OUTING_PROMPT
    assert "controlled research_family_outings wrapper" in OUTING_PROMPT
    assert "bypass it with you-answer or you-research" in OUTING_PROMPT
    assert "source URLs" in OUTING_PROMPT
    assert "Do not book" in OUTING_PROMPT
    assert '"This weekend" means the Saturday-Sunday pair' in OUTING_PROMPT
    assert "Never use Friday-Saturday" in OUTING_PROMPT
    assert "Never ask a parent to paste or provide an API key" in OUTING_PROMPT
    assert "HARD OUTING COMPLETION GATE" in COORDINATOR_PROMPT
    assert "Every recommended option must have a source URL" in COORDINATOR_PROMPT
    assert '"Conflict-free" refers only to the family' in OUTING_PROMPT
    assert 'Do not say "confirmed open"' in OUTING_PROMPT
    assert "extracted content from its official" in OUTING_PROMPT
    assert "must not be used as final evidence" in OUTING_PROMPT
    assert "unsupported_claims" in OUTING_PROMPT
    assert "nomadasaurus.com" in OUTING_PROMPT
    assert "A mapping tool is not required" in OUTING_PROMPT
    assert 'label it "estimated drive time"' in OUTING_PROMPT
    assert "verify it in a current maps app" in OUTING_PROMPT
    assert '"Estimated drive time — verify in maps"' in OUTING_PROMPT
    assert "Each must occur exactly three times" in OUTING_PROMPT
    assert "Family-calendar status:" in COORDINATOR_PROMPT
    assert "Not calculated; verify the route" in COORDINATOR_PROMPT
    assert "Do not recommend a school" in OUTING_PROMPT
    assert "public drop-in activity" in OUTING_PROMPT
    assert "curated" in OUTING_PROMPT
    assert "Never replace those returned URLs" in OUTING_PROMPT
    assert "Include public" in OUTING_PROMPT
    assert "hiking trails" in OUTING_PROMPT
    assert '"places to visit / things to do,"' in OUTING_PROMPT
    assert "focused science" in OUTING_PROMPT
    assert "Field trips, camps" in OUTING_PROMPT
    assert "Prefer self-guided destinations" in OUTING_PROMPT
    assert "exact date and an official event" in OUTING_PROMPT
    assert "Never say a weather, fire-danger" in OUTING_PROMPT
    assert 'Never say options are "comfortably reachable"' in OUTING_PROMPT
    assert "IMAX theater" in OUTING_PROMPT


def test_coordinator_requires_deep_weekly_workflow_and_review_loop():
    assert "DEEP WEEKLY WORKFLOW" in COORDINATOR_PROMPT
    assert "weekly-planner" in COORDINATOR_PROMPT
    assert "schedule-reviewer" in COORDINATOR_PROMPT
    assert "revision_required" in COORDINATOR_PROMPT
    assert "grouped set" in COORDINATOR_PROMPT
    assert "transportation-agent" in COORDINATOR_PROMPT
    assert "generate_schedule_candidates" in COORDINATOR_PROMPT
    assert "expected_version" in COORDINATOR_PROMPT
    assert "HARD COMPLETION GATE" in COORDINATOR_PROMPT
    assert "DATA-HANDOFF RULE" in COORDINATOR_PROMPT
    assert "Never ask the parent for information" in COORDINATOR_PROMPT
    assert "already returned during this run" in COORDINATOR_PROMPT
    assert "Never describe a plan" in COORDINATOR_PROMPT
    assert "reviewed without the review artifact" in COORDINATOR_PROMPT
    assert "Never suggest assigning one parent to simultaneous events" in COORDINATOR_PROMPT
    assert "explicit trade-off" in COORDINATOR_PROMPT
    assert "unchecked alternative time" in SCHEDULE_REVIEWER_PROMPT


def test_weekly_planner_and_reviewer_use_school_calendar():
    assert "list_school_events" in WEEKLY_PLANNER_PROMPT
    assert "check_school_conflicts" in WEEKLY_PLANNER_PROMPT
    assert "Never send YYYY-MM-DD to list_events" in WEEKLY_PLANNER_PROMPT
    assert "/work/weekly_schedule.json" in WEEKLY_PLANNER_PROMPT
    assert "/reviews/weekly_schedule_review.json" in SCHEDULE_REVIEWER_PROMPT
    assert "same-child overlaps" in SCHEDULE_REVIEWER_PROMPT
    assert "Vikram assigned" in SCHEDULE_REVIEWER_PROMPT
    assert "calendar fingerprint" in SCHEDULE_REVIEWER_PROMPT
    assert "review_schedule_candidate" in SCHEDULE_REVIEWER_PROMPT
    assert "copy only the tool's resolution_options" in SCHEDULE_REVIEWER_PROMPT
    assert "check_transportation_conflicts" in TRANSPORTATION_PROMPT
