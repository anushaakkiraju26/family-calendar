from datetime import datetime
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
    idempotency_key: str = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_times(self):
        if self.end_at is not None and self.end_at <= self.start_at:
            raise ValueError("end_at must be later than start_at")
        return self


class EventChanges(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    start_at: datetime | None = None
    end_at: datetime | None = None
    child_id: str | None = None
    location: str | None = None
    assigned_parent_id: str | None = None


class Event(BaseModel):
    id: str
    family_id: str
    title: str
    start_at: datetime
    end_at: datetime | None = None
    child_id: str | None = None
    location: str | None = None
    assigned_parent_id: str | None = None
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
