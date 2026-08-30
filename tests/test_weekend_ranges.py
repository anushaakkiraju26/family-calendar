from datetime import date

from family_activity_agent.agent import weekend_ranges


def test_this_weekend_when_reference_is_saturday():
    this_weekend, next_weekend = weekend_ranges(date(2026, 8, 29))
    assert this_weekend == (date(2026, 8, 29), date(2026, 8, 30))
    assert next_weekend == (date(2026, 9, 5), date(2026, 9, 6))


def test_this_weekend_when_reference_is_sunday():
    this_weekend, next_weekend = weekend_ranges(date(2026, 8, 30))
    assert this_weekend == (date(2026, 8, 29), date(2026, 8, 30))
    assert next_weekend == (date(2026, 9, 5), date(2026, 9, 6))


def test_this_weekend_when_reference_is_weekday():
    this_weekend, next_weekend = weekend_ranges(date(2026, 8, 26))
    assert this_weekend == (date(2026, 8, 29), date(2026, 8, 30))
    assert next_weekend == (date(2026, 9, 5), date(2026, 9, 6))
