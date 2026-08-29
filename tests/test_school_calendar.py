from datetime import date, datetime
from zoneinfo import ZoneInfo

from family_activity_mcp.school_calendar import (
    check_school_conflicts,
    list_school_events,
    load_school_events,
)


PACIFIC = ZoneInfo("America/Los_Angeles")


def test_attached_school_calendar_is_structured_and_spans_school_year():
    events = load_school_events()
    assert len(events) >= 75
    assert events[0]["start_date"] == "2026-08-03"
    assert events[-1]["start_date"] == "2027-05-27"


def test_list_school_events_includes_cross_month_fall_break():
    events = list_school_events(date(2026, 10, 1), date(2026, 10, 1))
    assert [event["title"] for event in events] == ["Fall Break"]


def test_timed_school_event_overlap_is_reported():
    conflicts = check_school_conflicts(
        datetime(2027, 5, 18, 17, 15, tzinfo=PACIFIC),
        datetime(2027, 5, 18, 17, 45, tzinfo=PACIFIC),
    )
    titles = {
        item["title"] for item in conflicts
        if item["kind"] == "school_event_overlap"
    }
    assert titles == {"Art Show", "Open House"}


def test_school_closure_removes_regular_school_hour_warning():
    conflicts = check_school_conflicts(
        datetime(2026, 11, 11, 10, tzinfo=PACIFIC),
        datetime(2026, 11, 11, 11, tzinfo=PACIFIC),
    )
    assert any(item["kind"] == "school_closure" for item in conflicts)
    assert not any(item["kind"] == "school_hours" for item in conflicts)


def test_early_dismissal_is_a_transportation_warning():
    conflicts = check_school_conflicts(
        datetime(2027, 5, 27, 12, 30, tzinfo=PACIFIC),
        datetime(2027, 5, 27, 14, 0, tzinfo=PACIFIC),
    )
    warning = next(item for item in conflicts if item["kind"] == "early_dismissal")
    assert warning["dismissal_time"] == "13:01"
    assert "Transportation" in warning["message"]
