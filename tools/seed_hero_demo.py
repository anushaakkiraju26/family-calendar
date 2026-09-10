"""Seed an isolated future-week database for the course hero workflow."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from family_activity_mcp.models import EventCreate
from family_activity_mcp.repository import CalendarRepository


PACIFIC = ZoneInfo("America/Los_Angeles")
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def next_monday(now: datetime) -> datetime:
    days = (7 - now.weekday()) % 7 or 7
    return (now + timedelta(days=days)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database",
        default=str(PROJECT_ROOT / "data" / "hero_demo.db"),
    )
    args = parser.parse_args()
    repository = CalendarRepository(args.database)
    monday = next_monday(datetime.now(PACIFIC))
    events = [
        EventCreate(
            family_id="family-1", title="Leo Soccer Practice",
            start_at=monday + timedelta(days=1, hours=16),
            end_at=monday + timedelta(days=1, hours=17), child_id="leo",
            location="Community Field", pickup_required=True,
            dropoff_required=True, idempotency_key=f"hero-soccer-{monday.date()}",
        ),
        EventCreate(
            family_id="family-1", title="Child-2 Music Lesson",
            start_at=monday + timedelta(days=1, hours=16),
            end_at=monday + timedelta(days=1, hours=17), child_id="child-2",
            location="Music School", pickup_required=True,
            dropoff_required=True, idempotency_key=f"hero-music-{monday.date()}",
        ),
        EventCreate(
            family_id="family-1", title="Classroom Volunteer Shift",
            start_at=monday + timedelta(days=2, hours=15, minutes=30),
            end_at=monday + timedelta(days=2, hours=16, minutes=30),
            child_id="leo", location="Maple Grove Elementary",
            idempotency_key=f"hero-volunteer-{monday.date()}",
        ),
    ]
    created = [repository.create_event(event) for event in events]
    print(f"Seeded {len(created)} events in {args.database}")
    print(f"Week: {monday.date()} through {(monday + timedelta(days=6)).date()}")


if __name__ == "__main__":
    main()
