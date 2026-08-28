from family_activity_agent.prompts import (
    CALENDAR_PROMPT,
    CONFLICT_PROMPT,
    COORDINATOR_PROMPT,
    INTAKE_PROMPT,
    REMINDER_PROMPT,
)


def test_file_writing_prompts_include_required_tool_arguments():
    for prompt in (
        INTAKE_PROMPT,
        CALENDAR_PROMPT,
        CONFLICT_PROMPT,
        REMINDER_PROMPT,
    ):
        assert "file_path" in prompt
        assert "content" in prompt


def test_coordinator_has_family_time_defaults():
    assert "America/Los_Angeles" in COORDINATOR_PROMPT
    assert "9:00 AM to 3:00 PM" in COORDINATOR_PROMPT
