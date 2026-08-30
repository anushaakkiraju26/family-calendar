"""Seed a realistic, idempotent month of events in the family calendar."""
from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from family_activity_mcp.models import EventCreate
from family_activity_mcp.repository import CalendarRepository


PACIFIC = ZoneInfo("America/Los_Angeles")
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def at(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), PACIFIC)


def event(
    start_day: date,
    title: str,
    start: tuple[int, int],
    end: tuple[int, int],
    key: str,
    **details,
) -> EventCreate:
    return EventCreate(
        family_id="family-1",
        title=title,
        start_at=at(start_day, *start),
        end_at=at(start_day, *end),
        idempotency_key=f"month-demo-{start_day.isoformat()}-{key}",
        **details,
    )


def build_events(start_day: date) -> list[EventCreate]:
    # Start on the first full day so seeding remains valid when run late today.
    first = start_day + timedelta(days=1)
    events = [
        event(first, "Family planning breakfast", (9, 0), (10, 0), "planning",
              location="Home", assigned_parent_id="parent-1"),
        event(first + timedelta(days=7), "Family hike", (9, 30), (12, 30), "hike",
              location="Alum Rock Park"),
        event(first + timedelta(days=13), "Kids science workshop", (10, 0), (12, 0),
              "science", child_id="leo", location="The Tech Interactive",
              assigned_parent_id="parent-2", pickup_required=True,
              dropoff_required=True),
        event(first + timedelta(days=21), "Maya's birthday party", (14, 0), (16, 30),
              "birthday", child_id="child-2", location="Community Center",
              assigned_parent_id="parent-1", pickup_required=True,
              dropoff_required=True),
        event(first + timedelta(days=27), "Family picnic", (11, 30), (14, 0), "picnic",
              location="Vasona Lake County Park"),
    ]

    # Parallel Tuesday activities intentionally exercise assignment and
    # transportation planning while remaining valid for different children.
    first_tuesday = first + timedelta(days=(1 - first.weekday()) % 7)
    for week in range(5):
        day = first_tuesday + timedelta(days=7 * week)
        if day > start_day + timedelta(days=31):
            break
        events.extend([
            event(day, "Leo soccer practice", (16, 0), (17, 30), "soccer",
                  child_id="leo", location="Community Field",
                  pickup_required=True, dropoff_required=True,
                  transportation_notes="Bring cleats and water."),
            event(day, "Child-2 piano lesson", (16, 0), (17, 0), "piano",
                  child_id="child-2", location="Music School",
                  pickup_required=True, dropoff_required=True,
                  transportation_notes="Bring music folder."),
        ])

    first_thursday = first + timedelta(days=(3 - first.weekday()) % 7)
    for week in range(4):
        day = first_thursday + timedelta(days=7 * week)
        events.append(event(
            day, "Leo swim practice", (17, 0), (18, 0), "swim",
            child_id="leo", location="Aquatic Center",
            assigned_parent_id="parent-2", pickup_required=True,
            dropoff_required=True,
        ))

    events.extend([
        event(date(2026, 9, 9), "Child-2 dentist appointment", (13, 0), (14, 0),
              "dentist", child_id="child-2", location="San Jose Pediatric Dental",
              assigned_parent_id="parent-1", pickup_required=True,
              dropoff_required=True),
        event(date(2026, 9, 17), "Parent-teacher conference", (14, 30), (15, 15),
              "conference", child_id="leo", location="Reed Elementary",
              assigned_parent_id="parent-1"),
    ])
    return sorted(events, key=lambda item: item.start_at)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database", default=str(PROJECT_ROOT / "data" / "family_activity.db")
    )
    parser.add_argument("--start", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()

    repository = CalendarRepository(args.database)
    seeded = [repository.create_event(item) for item in build_events(args.start)]
    print(f"Calendar contains {len(seeded)} month-demo events (idempotent seed).")
    print(f"Range: {seeded[0].start_at.date()} through {seeded[-1].start_at.date()}")


if __name__ == "__main__":
    main()
