from datetime import datetime, timedelta, timezone

import pytest

from family_activity_mcp.models import EventChanges, EventCreate
from family_activity_mcp.repository import CalendarRepository


def create(repository):
    start = datetime(2026, 9, 1, 16, tzinfo=timezone.utc)
    return repository.create_event(EventCreate(
        family_id="family-1", title="Soccer", start_at=start,
        end_at=start + timedelta(hours=1), child_id="leo",
        idempotency_key="request-1",
    ))


def test_lifecycle_and_idempotency(tmp_path):
    repository = CalendarRepository(str(tmp_path / "test.db"))
    event = create(repository)
    assert create(repository).id == event.id
    reminder = repository.schedule_reminder(
        "family-1", event.id, "parent-1",
        event.start_at - timedelta(hours=8), "sms", "Leo has soccer today.",
    )
    assert reminder.status == "scheduled"
    assert reminder.message_body == "Leo has soccer today."
    updated = repository.update_event(
        "family-1", event.id, EventChanges(location="West Field"), event.version
    )
    deleted = repository.delete_event(
        "family-1", event.id, updated.version, "Cancelled"
    )
    assert deleted.status == "deleted"
    assert repository.list_events("family-1") == []
    assert repository.list_events("family-1", include_deleted=True)[0].id == event.id
    assert repository.restore_event("family-1", event.id).status == "active"


def test_conflicts_and_version_guard(tmp_path):
    repository = CalendarRepository(str(tmp_path / "test.db"))
    event = create(repository)
    conflicts = repository.check_conflicts(
        "family-1", event.start_at + timedelta(minutes=30),
        event.end_at + timedelta(hours=1), "leo",
    )
    assert [item.id for item in conflicts] == [event.id]
    with pytest.raises(ValueError, match="version conflict"):
        repository.update_event(
            "family-1", event.id, EventChanges(title="Changed"), 99
        )


def test_schedule_day_of_reminders_for_both_parents_is_idempotent(tmp_path):
    repository = CalendarRepository(str(tmp_path / "test.db"))
    event = create(repository)
    send_at = event.start_at.replace(hour=8, minute=0)

    reminders = repository.schedule_day_of_reminders(
        "family-1", event.id, ["parent-1", "parent-2"], send_at, "sms",
        "Reminder: Leo has soccer today at 4 PM.",
    )
    assert [item.recipient_id for item in reminders] == [
        "parent-1", "parent-2"
    ]
    assert all(item.status == "scheduled" for item in reminders)

    repeated = repository.schedule_day_of_reminders(
        "family-1", event.id, ["parent-1", "parent-2"], send_at, "sms",
        "Updated draft: Leo has soccer today at 4 PM.",
    )
    assert [item.id for item in repeated] == [item.id for item in reminders]
    assert all(
        item.message_body == "Updated draft: Leo has soccer today at 4 PM."
        for item in repeated
    )
    assert len(repository.list_reminders("family-1", event.id)) == 2


def test_day_of_reminder_rejects_wrong_date(tmp_path):
    repository = CalendarRepository(str(tmp_path / "test.db"))
    event = create(repository)
    with pytest.raises(ValueError, match="event date"):
        repository.schedule_day_of_reminders(
            "family-1", event.id, ["parent-1", "parent-2"],
            event.start_at - timedelta(days=1), "sms", "Soccer reminder.",
        )


def test_create_event_rejects_past_and_naive_start_times(tmp_path):
    repository = CalendarRepository(str(tmp_path / "test.db"))
    for start_at, message in (
        (datetime.now(timezone.utc) - timedelta(minutes=1), "future"),
        (datetime(2026, 9, 1, 16), "timezone-aware"),
    ):
        with pytest.raises(ValueError, match=message):
            repository.create_event(EventCreate(
                family_id="family-1", title="Invalid event",
                start_at=start_at, idempotency_key=f"invalid-{message}",
            ))


def test_update_event_rejects_moving_event_to_past(tmp_path):
    repository = CalendarRepository(str(tmp_path / "test.db"))
    event = create(repository)
    with pytest.raises(ValueError, match="future"):
        repository.update_event(
            "family-1", event.id,
            EventChanges(start_at=datetime.now(timezone.utc) - timedelta(minutes=1)),
            event.version,
        )


def test_create_rejects_same_child_overlap_but_allows_different_child(tmp_path):
    repository = CalendarRepository(str(tmp_path / "test.db"))
    event = create(repository)
    with pytest.raises(ValueError, match="schedule conflict"):
        repository.create_event(EventCreate(
            family_id="family-1", title="Overlapping practice",
            start_at=event.start_at + timedelta(minutes=15),
            end_at=event.end_at, child_id="leo",
            idempotency_key="same-child-overlap",
        ))

    allowed = repository.create_event(EventCreate(
        family_id="family-1", title="Music",
        start_at=event.start_at, end_at=event.end_at,
        child_id="child-2", idempotency_key="different-child-overlap",
    ))
    assert allowed.child_id == "child-2"


def test_update_rejects_assigning_same_parent_to_overlapping_events(tmp_path):
    repository = CalendarRepository(str(tmp_path / "test.db"))
    first = create(repository)
    second = repository.create_event(EventCreate(
        family_id="family-1", title="Music",
        start_at=first.start_at, end_at=first.end_at,
        child_id="child-2", idempotency_key="music",
    ))
    first = repository.update_event(
        "family-1", first.id, EventChanges(assigned_parent_id="parent-1"),
        first.version,
    )
    with pytest.raises(ValueError, match="schedule conflict"):
        repository.update_event(
            "family-1", second.id,
            EventChanges(assigned_parent_id="parent-1"), second.version,
        )

    unchanged = repository.list_events("family-1", child_id="child-2")[0]
    assert unchanged.assigned_parent_id is None
