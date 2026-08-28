import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .models import Event, EventChanges, EventCreate, Reminder


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def require_future_start(start_at: datetime) -> None:
    """Reject ambiguous or past event start times at the persistence boundary."""
    if start_at.tzinfo is None or start_at.utcoffset() is None:
        raise ValueError("event start_at must be timezone-aware")
    if start_at <= datetime.now(timezone.utc):
        raise ValueError("event start_at must be in the future")


class CalendarRepository:
    def __init__(self, database_path: str):
        self.database_path = database_path
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY, family_id TEXT NOT NULL, title TEXT NOT NULL,
                    start_at TEXT NOT NULL, end_at TEXT, child_id TEXT, location TEXT,
                    assigned_parent_id TEXT, status TEXT NOT NULL DEFAULT 'active',
                    version INTEGER NOT NULL DEFAULT 1, idempotency_key TEXT NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    deleted_at TEXT, deletion_reason TEXT,
                    UNIQUE(family_id, idempotency_key)
                );
                CREATE INDEX IF NOT EXISTS idx_events_family_time
                    ON events(family_id, start_at, end_at);
                CREATE TABLE IF NOT EXISTS reminders (
                    id TEXT PRIMARY KEY, event_id TEXT NOT NULL REFERENCES events(id),
                    family_id TEXT NOT NULL, recipient_id TEXT NOT NULL,
                    send_at TEXT NOT NULL, channel TEXT NOT NULL,
                    message_body TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'scheduled',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id TEXT PRIMARY KEY, family_id TEXT NOT NULL, action TEXT NOT NULL,
                    entity_id TEXT NOT NULL, before_state TEXT, after_state TEXT,
                    created_at TEXT NOT NULL
                );
            """)
            reminder_columns = {
                row["name"] for row in db.execute("PRAGMA table_info(reminders)")
            }
            if "message_body" not in reminder_columns:
                db.execute(
                    "ALTER TABLE reminders ADD COLUMN message_body TEXT NOT NULL DEFAULT ''"
                )

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database_path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_row(self, db, family_id: str, event_id: str):
        row = db.execute(
            "SELECT * FROM events WHERE family_id=? AND id=?", (family_id, event_id)
        ).fetchone()
        if row is None:
            raise ValueError("event not found in this family")
        return row

    def conflicting_rows(
        self, db, family_id, start_at, end_at, child_id=None,
        assigned_parent_id=None, exclude_event_id=None,
    ):
        """Return deterministic child/parent overlaps using parsed timestamps."""
        if not child_id and not assigned_parent_id:
            return []
        proposed_end = end_at or start_at
        rows = db.execute(
            "SELECT * FROM events WHERE family_id=? AND status='active'",
            (family_id,),
        ).fetchall()
        conflicts = []
        for row in rows:
            if exclude_event_id and row["id"] == exclude_event_id:
                continue
            same_child = bool(child_id and row["child_id"] == child_id)
            same_parent = bool(
                assigned_parent_id
                and row["assigned_parent_id"] == assigned_parent_id
            )
            if not (same_child or same_parent):
                continue
            existing_start = datetime.fromisoformat(row["start_at"])
            existing_end = (
                datetime.fromisoformat(row["end_at"])
                if row["end_at"] else existing_start
            )
            if start_at < existing_end and proposed_end > existing_start:
                conflicts.append(row)
        return conflicts

    def require_no_conflicts(
        self, db, family_id, start_at, end_at, child_id=None,
        assigned_parent_id=None, exclude_event_id=None,
    ):
        conflicts = self.conflicting_rows(
            db, family_id, start_at, end_at, child_id,
            assigned_parent_id, exclude_event_id,
        )
        if conflicts:
            details = ", ".join(
                f"{row['title']} ({row['id']})" for row in conflicts
            )
            raise ValueError(f"schedule conflict with {details}")

    def audit(self, db, family_id, action, entity_id, before=None, after=None):
        db.execute(
            "INSERT INTO audit_logs VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(uuid4()), family_id, action, entity_id,
             json.dumps(before, default=str) if before else None,
             json.dumps(after, default=str) if after else None, now_iso()),
        )

    def create_event(self, data: EventCreate) -> Event:
        require_future_start(data.start_at)
        with self.connect() as db:
            existing = db.execute(
                "SELECT * FROM events WHERE family_id=? AND idempotency_key=?",
                (data.family_id, data.idempotency_key),
            ).fetchone()
            if existing:
                return Event.model_validate(dict(existing))
            self.require_no_conflicts(
                db, data.family_id, data.start_at, data.end_at,
                data.child_id, data.assigned_parent_id,
            )
            event_id, timestamp = str(uuid4()), now_iso()
            db.execute(
                """INSERT INTO events
                (id,family_id,title,start_at,end_at,child_id,location,assigned_parent_id,
                 status,version,idempotency_key,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,'active',1,?,?,?)""",
                (event_id, data.family_id, data.title, iso(data.start_at), iso(data.end_at),
                 data.child_id, data.location, data.assigned_parent_id,
                 data.idempotency_key, timestamp, timestamp),
            )
            row = self.get_row(db, data.family_id, event_id)
            self.audit(db, data.family_id, "event.created", event_id, after=dict(row))
            return Event.model_validate(dict(row))

    def list_events(self, family_id, start_at=None, end_at=None, child_id=None, include_deleted=False):
        clauses, params = ["family_id=?"], [family_id]
        if not include_deleted:
            clauses.append("status='active'")
        if start_at:
            clauses.append("COALESCE(end_at,start_at)>=?")
            params.append(iso(start_at))
        if end_at:
            clauses.append("start_at<=?")
            params.append(iso(end_at))
        if child_id:
            clauses.append("child_id=?")
            params.append(child_id)
        with self.connect() as db:
            rows = db.execute(
                f"SELECT * FROM events WHERE {' AND '.join(clauses)} ORDER BY start_at", params
            ).fetchall()
            return [Event.model_validate(dict(row)) for row in rows]

    def update_event(self, family_id, event_id, changes: EventChanges, expected_version):
        values = changes.model_dump(exclude_unset=True)
        if not values:
            raise ValueError("at least one change is required")
        if "start_at" in values:
            require_future_start(values["start_at"])
        with self.connect() as db:
            before = self.get_row(db, family_id, event_id)
            if before["status"] == "deleted":
                raise ValueError("restore the event before updating it")
            if before["version"] != expected_version:
                raise ValueError(f"version conflict: current version is {before['version']}")
            start = values.get("start_at") or datetime.fromisoformat(before["start_at"])
            end = values.get("end_at")
            if "end_at" not in values and before["end_at"]:
                end = datetime.fromisoformat(before["end_at"])
            if end and end <= start:
                raise ValueError("end_at must be later than start_at")
            if set(values) & {
                "start_at", "end_at", "child_id", "assigned_parent_id"
            }:
                self.require_no_conflicts(
                    db, family_id, start, end,
                    values.get("child_id", before["child_id"]),
                    values.get("assigned_parent_id", before["assigned_parent_id"]),
                    event_id,
                )
            values["updated_at"] = now_iso()
            assignments = ",".join(f"{key}=?" for key in values) + ",version=version+1"
            encoded = [iso(v) if isinstance(v, datetime) else v for v in values.values()]
            db.execute(f"UPDATE events SET {assignments} WHERE family_id=? AND id=?",
                       [*encoded, family_id, event_id])
            after = self.get_row(db, family_id, event_id)
            self.audit(db, family_id, "event.updated", event_id, dict(before), dict(after))
            return Event.model_validate(dict(after))

    def delete_event(self, family_id, event_id, expected_version, reason=None):
        with self.connect() as db:
            before = self.get_row(db, family_id, event_id)
            if before["version"] != expected_version:
                raise ValueError(f"version conflict: current version is {before['version']}")
            timestamp = now_iso()
            db.execute(
                """UPDATE events SET status='deleted',deleted_at=?,deletion_reason=?,
                updated_at=?,version=version+1 WHERE family_id=? AND id=?""",
                (timestamp, reason, timestamp, family_id, event_id),
            )
            db.execute(
                "UPDATE reminders SET status='cancelled' WHERE event_id=? AND status='scheduled'",
                (event_id,),
            )
            after = self.get_row(db, family_id, event_id)
            self.audit(db, family_id, "event.deleted", event_id, dict(before), dict(after))
            return Event.model_validate(dict(after))

    def restore_event(self, family_id, event_id):
        with self.connect() as db:
            before = self.get_row(db, family_id, event_id)
            if before["status"] != "deleted":
                raise ValueError("event is not deleted")
            db.execute(
                """UPDATE events SET status='active',deleted_at=NULL,deletion_reason=NULL,
                updated_at=?,version=version+1 WHERE family_id=? AND id=?""",
                (now_iso(), family_id, event_id),
            )
            after = self.get_row(db, family_id, event_id)
            self.audit(db, family_id, "event.restored", event_id, dict(before), dict(after))
            return Event.model_validate(dict(after))

    def check_conflicts(self, family_id, start_at, end_at, child_id=None,
                        assigned_parent_id=None, exclude_event_id=None):
        if end_at <= start_at:
            raise ValueError("end_at must be later than start_at")
        clauses = ["family_id=?", "status='active'", "start_at<?",
                   "COALESCE(end_at,start_at)>?"]
        params: list[Any] = [family_id, iso(end_at), iso(start_at)]
        people = []
        if child_id:
            people.append("child_id=?")
            params.append(child_id)
        if assigned_parent_id:
            people.append("assigned_parent_id=?")
            params.append(assigned_parent_id)
        if people:
            clauses.append(f"({' OR '.join(people)})")
        if exclude_event_id:
            clauses.append("id!=?")
            params.append(exclude_event_id)
        with self.connect() as db:
            rows = db.execute(
                f"SELECT * FROM events WHERE {' AND '.join(clauses)} ORDER BY start_at", params
            ).fetchall()
            return [Event.model_validate(dict(row)) for row in rows]

    def schedule_reminder(
        self, family_id, event_id, recipient_id, send_at, channel, message_body
    ):
        if channel not in {"sms", "push", "email"}:
            raise ValueError("channel must be sms, push, or email")
        if not message_body.strip():
            raise ValueError("message_body is required")
        with self.connect() as db:
            event = self.get_row(db, family_id, event_id)
            if event["status"] != "active":
                raise ValueError("cannot schedule a reminder for a deleted event")
            reminder_id, timestamp = str(uuid4()), now_iso()
            db.execute(
                """INSERT INTO reminders
                (id,event_id,family_id,recipient_id,send_at,channel,message_body,status,created_at)
                VALUES (?,?,?,?,?,?,?,'scheduled',?)""",
                (
                    reminder_id, event_id, family_id, recipient_id,
                    iso(send_at), channel, message_body.strip(), timestamp,
                ),
            )
            row = db.execute("SELECT * FROM reminders WHERE id=?", (reminder_id,)).fetchone()
            self.audit(db, family_id, "reminder.scheduled", reminder_id, after=dict(row))
            return Reminder.model_validate(dict(row))

    def schedule_day_of_reminders(
        self, family_id, event_id, recipient_ids, send_at, channel="sms",
        message_body="",
    ):
        if channel not in {"sms", "push", "email"}:
            raise ValueError("channel must be sms, push, or email")
        recipients = list(dict.fromkeys(recipient_ids))
        if not recipients:
            raise ValueError("at least one recipient_id is required")
        if any(not recipient.strip() for recipient in recipients):
            raise ValueError("recipient_ids cannot contain blank values")
        if not message_body.strip():
            raise ValueError("message_body is required")

        with self.connect() as db:
            event = self.get_row(db, family_id, event_id)
            if event["status"] != "active":
                raise ValueError("cannot schedule reminders for a deleted event")
            event_start = datetime.fromisoformat(event["start_at"])
            if send_at.tzinfo is None or event_start.tzinfo is None:
                raise ValueError("event and reminder times must be timezone-aware")
            if send_at.date() != event_start.date():
                raise ValueError("day-of reminder must be on the event date")
            if send_at >= event_start:
                raise ValueError("reminder must be scheduled before the event starts")
            if send_at <= datetime.now(send_at.tzinfo):
                raise ValueError("reminder send_at must be in the future")

            reminders = []
            for recipient_id in recipients:
                existing = db.execute(
                    """SELECT * FROM reminders
                    WHERE family_id=? AND event_id=? AND recipient_id=?
                      AND send_at=? AND channel=? AND status IN ('scheduled','sent')""",
                    (family_id, event_id, recipient_id, iso(send_at), channel),
                ).fetchone()
                if existing:
                    if existing["message_body"] != message_body.strip():
                        db.execute(
                            "UPDATE reminders SET message_body=? WHERE id=?",
                            (message_body.strip(), existing["id"]),
                        )
                        existing = db.execute(
                            "SELECT * FROM reminders WHERE id=?", (existing["id"],)
                        ).fetchone()
                    reminders.append(Reminder.model_validate(dict(existing)))
                    continue

                reminder_id, timestamp = str(uuid4()), now_iso()
                db.execute(
                    """INSERT INTO reminders
                    (id,event_id,family_id,recipient_id,send_at,channel,message_body,status,created_at)
                    VALUES (?,?,?,?,?,?,?,'scheduled',?)""",
                    (
                        reminder_id, event_id, family_id, recipient_id,
                        iso(send_at), channel, message_body.strip(), timestamp,
                    ),
                )
                row = db.execute(
                    "SELECT * FROM reminders WHERE id=?", (reminder_id,)
                ).fetchone()
                reminders.append(Reminder.model_validate(dict(row)))

            self.audit(
                db, family_id, "reminders.day_of_scheduled", event_id,
                after={
                    "reminder_ids": [reminder.id for reminder in reminders],
                    "recipient_ids": recipients,
                    "send_at": iso(send_at),
                    "channel": channel,
                    "message_body": message_body.strip(),
                },
            )
            return reminders

    def list_reminders(self, family_id, event_id, include_cancelled=False):
        clauses = ["family_id=?", "event_id=?"]
        params = [family_id, event_id]
        if not include_cancelled:
            clauses.append("status!='cancelled'")
        with self.connect() as db:
            rows = db.execute(
                f"SELECT * FROM reminders WHERE {' AND '.join(clauses)} ORDER BY send_at, recipient_id",
                params,
            ).fetchall()
            return [Reminder.model_validate(dict(row)) for row in rows]

    def cancel_reminders(self, family_id, event_id):
        with self.connect() as db:
            self.get_row(db, family_id, event_id)
            cursor = db.execute(
                """UPDATE reminders SET status='cancelled'
                WHERE family_id=? AND event_id=? AND status='scheduled'""",
                (family_id, event_id),
            )
            self.audit(db, family_id, "reminders.cancelled", event_id,
                       after={"count": cursor.rowcount})
            return cursor.rowcount
