from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class EventCreate(BaseModel):
    family_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=200)
    start_at: datetime
    end_at: datetime | None = None
    child_id: str | None = None
    location: str | None = None
    assigned_parent_id: str | None = None
    pickup_required: bool = False
    dropoff_required: bool = False
    pickup_at: datetime | None = None
    dropoff_at: datetime | None = None
    transportation_notes: str | None = None
    idempotency_key: str = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_times(self):
        if self.end_at is not None and self.end_at <= self.start_at:
            raise ValueError("end_at must be later than start_at")
        if self.pickup_at is not None:
            if self.pickup_at.tzinfo is None:
                raise ValueError("pickup_at must be timezone-aware")
            if self.pickup_at > self.start_at:
                raise ValueError("pickup_at cannot be after event start_at")
        if self.dropoff_at is not None:
            if self.dropoff_at.tzinfo is None:
                raise ValueError("dropoff_at must be timezone-aware")
            if self.end_at is not None and self.dropoff_at < self.end_at:
                raise ValueError("dropoff_at cannot be before event end_at")
        return self


class EventChanges(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    start_at: datetime | None = None
    end_at: datetime | None = None
    child_id: str | None = None
    location: str | None = None
    assigned_parent_id: str | None = None
    pickup_required: bool | None = None
    dropoff_required: bool | None = None
    pickup_at: datetime | None = None
    dropoff_at: datetime | None = None
    transportation_notes: str | None = None


class Event(BaseModel):
    id: str
    family_id: str
    title: str
    start_at: datetime
    end_at: datetime | None = None
    child_id: str | None = None
    location: str | None = None
    assigned_parent_id: str | None = None
    pickup_required: bool = False
    dropoff_required: bool = False
    pickup_at: datetime | None = None
    dropoff_at: datetime | None = None
    transportation_notes: str | None = None
    status: Literal["active", "deleted"]
    version: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    deletion_reason: str | None = None


class Reminder(BaseModel):
    id: str
    event_id: str
    family_id: str
    recipient_id: str
    send_at: datetime
    channel: Literal["sms", "push", "email"]
    message_body: str = ""
    status: Literal["scheduled", "cancelled", "sent"]
    created_at: datetime


class AvailabilityRule(BaseModel):
    id: str
    family_id: str
    parent_id: str
    day_of_week: int = Field(ge=0, le=6)
    unavailable_start: time
    unavailable_end: time
    timezone: str = "America/Los_Angeles"
    reason: str
    effective_start: date | None = None
    effective_end: date | None = None


class TransportationRequirement(BaseModel):
    requirement_id: str
    event_id: str
    event_version: int
    child_id: str | None = None
    requirement_type: Literal["pickup", "dropoff", "event_coverage"]
    required_start: datetime
    required_end: datetime
    origin: str | None = None
    destination: str | None = None


class CandidateAssignment(BaseModel):
    event_id: str
    expected_version: int
    assigned_parent_id: str


class ScheduleCandidate(BaseModel):
    candidate_id: str
    assignments: list[CandidateAssignment]
    transportation: list[dict]
    conflicts: list[dict]
    warnings: list[dict]
    score: float
    rationale: list[str]


class CandidateSet(BaseModel):
    family_id: str
    generated_at: datetime
    calendar_fingerprint: str
    candidates: list[ScheduleCandidate]
    recommended_candidate_id: str | None
