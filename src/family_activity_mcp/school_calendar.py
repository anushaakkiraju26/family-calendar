from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


PACIFIC = ZoneInfo("America/Los_Angeles")
DEFAULT_CALENDAR = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "reed_elementary_2026_2027.json"
)


def load_school_events(path: Path = DEFAULT_CALENDAR) -> list[dict[str, Any]]:
    """Load the reviewed transcription of the attached school calendar."""
    payload = json.loads(path.read_text())
    return payload["events"]


def event_dates(event: dict[str, Any]):
    current = date.fromisoformat(event["start_date"])
    end = date.fromisoformat(event.get("end_date", event["start_date"]))
    while current <= end:
        yield current
        current += timedelta(days=1)


def list_school_events(
    start_date: date, end_date: date, path: Path = DEFAULT_CALENDAR
) -> list[dict[str, Any]]:
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")
    matches = []
    for event in load_school_events(path):
        if any(start_date <= day <= end_date for day in event_dates(event)):
            matches.append(event)
    return matches


def _clock(value: str | None, default: time) -> time:
    return time.fromisoformat(value) if value else default


def check_school_conflicts(
    start_at: datetime,
    end_at: datetime,
    path: Path = DEFAULT_CALENDAR,
) -> list[dict[str, Any]]:
    """Return deterministic school-hour overlaps and dated school-calendar notes."""
    if start_at.tzinfo is None or end_at.tzinfo is None:
        raise ValueError("school conflict times must be timezone-aware")
    if end_at <= start_at:
        raise ValueError("end_at must be later than start_at")

    local_start = start_at.astimezone(PACIFIC)
    local_end = end_at.astimezone(PACIFIC)
    results: list[dict[str, Any]] = []

    current = local_start.date()
    while current <= local_end.date():
        day_start = datetime.combine(current, time.min, PACIFIC)
        day_end = datetime.combine(current, time.max, PACIFIC)
        interval_start = max(local_start, day_start)
        interval_end = min(local_end, day_end)

        if current.weekday() < 5:
            school_start = datetime.combine(current, time(9), PACIFIC)
            school_end = datetime.combine(current, time(15), PACIFIC)
            if interval_start < school_end and interval_end > school_start:
                results.append({
                    "kind": "school_hours",
                    "severity": "warning",
                    "date": current.isoformat(),
                    "title": "Regular school hours",
                    "start_at": school_start.isoformat(),
                    "end_at": school_end.isoformat(),
                    "message": "The activity overlaps regular school hours (9 AM–3 PM).",
                })

        for event in list_school_events(current, current, path):
            category = event["category"]
            if category == "closure":
                results.append({
                    "kind": "school_closure",
                    "severity": "info",
                    "date": current.isoformat(),
                    "title": event["title"],
                    "message": "School is closed; normal school-hour assumptions do not apply.",
                })
                continue
            if category == "early_dismissal":
                results.append({
                    "kind": "early_dismissal",
                    "severity": "warning",
                    "date": current.isoformat(),
                    "title": event["title"],
                    "dismissal_time": event.get("start_time", "13:01"),
                    "message": "Transportation or supervision may be needed after early dismissal.",
                })
                continue
            if not event.get("start_time"):
                results.append({
                    "kind": "school_event_note",
                    "severity": "info",
                    "date": current.isoformat(),
                    "title": event["title"],
                    "message": "A school event is scheduled on this date; no exact time was published.",
                })
                continue
            event_start = datetime.combine(
                current, _clock(event.get("start_time"), time.min), PACIFIC
            )
            event_end = datetime.combine(
                current,
                _clock(event.get("end_time"), _clock(event.get("start_time"), time.min)),
                PACIFIC,
            )
            if event_end == event_start:
                event_end += timedelta(minutes=30)
            if interval_start < event_end and interval_end > event_start:
                results.append({
                    "kind": "school_event_overlap",
                    "severity": "conflict",
                    "date": current.isoformat(),
                    "title": event["title"],
                    "start_at": event_start.isoformat(),
                    "end_at": event_end.isoformat(),
                    "message": "The activity overlaps a timed school-calendar event.",
                })
        current += timedelta(days=1)

    closures = {item["date"] for item in results if item["kind"] == "school_closure"}
    if closures:
        results = [
            item for item in results
            if not (item["kind"] == "school_hours" and item["date"] in closures)
        ]
    return results
