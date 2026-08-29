import argparse
import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .models import EventChanges, EventCreate
from .repository import CalendarRepository
from .school_calendar import (
    check_school_conflicts as find_school_conflicts,
    list_school_events as find_school_events,
)

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "family_activity.db"
repository = CalendarRepository(os.getenv("FAMILY_ACTIVITY_DB", str(DEFAULT_DB)))
mcp = FastMCP(
    "Family Activity Tools",
    instructions=(
        "Shared family calendar tools. Obtain explicit user confirmation before "
        "updates, deletion, restoration, or scheduling notifications."
    ),
)


def output(value: Any) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    if isinstance(value, list):
        value = [
            item.model_dump(mode="json") if hasattr(item, "model_dump") else item
            for item in value
        ]
    return json.dumps(value, default=str)


@mcp.tool()
def create_event(
    family_id: str, title: str, start_at: datetime, idempotency_key: str,
    end_at: datetime | None = None, child_id: str | None = None,
    location: str | None = None, assigned_parent_id: str | None = None,
) -> str:
    """Create one event; rejects same-child or same-parent time conflicts."""
    return output(repository.create_event(EventCreate(
        family_id=family_id, title=title, start_at=start_at, end_at=end_at,
        child_id=child_id, location=location,
        assigned_parent_id=assigned_parent_id, idempotency_key=idempotency_key,
    )))


@mcp.tool()
def list_events(
    family_id: str, start_at: datetime | None = None,
    end_at: datetime | None = None, child_id: str | None = None,
    include_deleted: bool = False,
) -> str:
    """List events, optionally filtered by time, child, and deletion status."""
    return output(repository.list_events(
        family_id, start_at, end_at, child_id, include_deleted
    ))


@mcp.tool()
def update_event(
    family_id: str, event_id: str, expected_version: int,
    title: str | None = None, start_at: datetime | None = None,
    end_at: datetime | None = None, child_id: str | None = None,
    location: str | None = None, assigned_parent_id: str | None = None,
) -> str:
    """Update an event; rejects conflicts and uses version to prevent lost updates."""
    supplied = {key: value for key, value in {
        "title": title, "start_at": start_at, "end_at": end_at,
        "child_id": child_id, "location": location,
        "assigned_parent_id": assigned_parent_id,
    }.items() if value is not None}
    return output(repository.update_event(
        family_id, event_id, EventChanges.model_validate(supplied), expected_version
    ))


@mcp.tool()
def delete_event(
    family_id: str, event_id: str, expected_version: int,
    deletion_reason: str | None = None,
) -> str:
    """Soft-delete a confirmed event and cancel its pending reminders."""
    return output(repository.delete_event(
        family_id, event_id, expected_version, deletion_reason
    ))


@mcp.tool()
def restore_event(family_id: str, event_id: str) -> str:
    """Restore a soft-deleted event after user confirmation."""
    return output(repository.restore_event(family_id, event_id))


@mcp.tool()
def check_conflicts(
    family_id: str, start_at: datetime, end_at: datetime,
    child_id: str | None = None, assigned_parent_id: str | None = None,
    exclude_event_id: str | None = None,
) -> str:
    """Find overlapping active events for a child or assigned parent."""
    return output(repository.check_conflicts(
        family_id, start_at, end_at, child_id,
        assigned_parent_id, exclude_event_id
    ))


@mcp.tool()
def list_school_events(start_date: date, end_date: date) -> str:
    """List Reed Elementary events, closures, and early-dismissal dates."""
    return output(find_school_events(start_date, end_date))


@mcp.tool()
def check_school_conflicts(start_at: datetime, end_at: datetime) -> str:
    """Check a proposed activity against school hours and the school calendar."""
    return output(find_school_conflicts(start_at, end_at))


@mcp.tool()
def schedule_reminder(
    family_id: str, event_id: str, recipient_id: str, send_at: datetime,
    message_body: str, channel: str = "sms",
) -> str:
    """Save a confirmed reminder draft for an active event; does not send it."""
    return output(repository.schedule_reminder(
        family_id, event_id, recipient_id, send_at, channel, message_body
    ))


@mcp.tool()
def schedule_day_of_reminders(
    family_id: str,
    event_id: str,
    recipient_ids: list[str],
    send_at: datetime,
    message_body: str,
    channel: str = "sms",
) -> str:
    """Save one day-of reminder draft per recipient; does not send messages."""
    return output(repository.schedule_day_of_reminders(
        family_id, event_id, recipient_ids, send_at, channel, message_body
    ))


@mcp.tool()
def list_reminders(
    family_id: str, event_id: str, include_cancelled: bool = False
) -> str:
    """List reminders for one family event."""
    return output(repository.list_reminders(
        family_id, event_id, include_cancelled
    ))


@mcp.tool()
def cancel_reminders(family_id: str, event_id: str) -> str:
    """Cancel all pending reminders for an event."""
    return output({
        "cancelled_count": repository.cancel_reminders(family_id, event_id)
    })


def main() -> None:
    parser = argparse.ArgumentParser(description="Family Activity MCP server")
    parser.add_argument(
        "--transport", choices=("stdio", "streamable-http"),
        default="streamable-http",
    )
    args = parser.parse_args()
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
