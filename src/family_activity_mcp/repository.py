import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
from itertools import product
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Any
from uuid import uuid4

from .models import (
    AvailabilityRule, CandidateAssignment, CandidateSet, Event, EventChanges,
    EventCreate, Reminder, ScheduleCandidate,
)

PACIFIC = ZoneInfo("America/Los_Angeles")


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
                CREATE TABLE IF NOT EXISTS availability_rules (
                    id TEXT PRIMARY KEY, family_id TEXT NOT NULL,
                    parent_id TEXT NOT NULL, day_of_week INTEGER NOT NULL,
                    unavailable_start TEXT NOT NULL, unavailable_end TEXT NOT NULL,
                    timezone TEXT NOT NULL, reason TEXT NOT NULL,
                    effective_start TEXT, effective_end TEXT
                );
            """)
            reminder_columns = {
                row["name"] for row in db.execute("PRAGMA table_info(reminders)")
            }
            if "message_body" not in reminder_columns:
                db.execute(
                    "ALTER TABLE reminders ADD COLUMN message_body TEXT NOT NULL DEFAULT ''"
                )
            event_columns = {
                row["name"] for row in db.execute("PRAGMA table_info(events)")
            }
            for name, definition in {
                "pickup_required": "INTEGER NOT NULL DEFAULT 0",
                "dropoff_required": "INTEGER NOT NULL DEFAULT 0",
                "pickup_at": "TEXT",
                "dropoff_at": "TEXT",
                "transportation_notes": "TEXT",
            }.items():
                if name not in event_columns:
                    db.execute(f"ALTER TABLE events ADD COLUMN {name} {definition}")
            for day in (1, 2, 3):
                db.execute(
                    """INSERT OR IGNORE INTO availability_rules
                    VALUES (?, 'family-1', 'vikram', ?, '09:30', '16:00',
                    'America/Los_Angeles', 'Work schedule', NULL, NULL)""",
                    (f"family-1-vikram-{day}-work", day),
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
                 status,version,idempotency_key,created_at,updated_at,pickup_required,
                 dropoff_required,pickup_at,dropoff_at,transportation_notes)
                VALUES (?,?,?,?,?,?,?,?,'active',1,?,?,?,?,?,?,?,?)""",
                (event_id, data.family_id, data.title, iso(data.start_at), iso(data.end_at),
                 data.child_id, data.location, data.assigned_parent_id,
                 data.idempotency_key, timestamp, timestamp,
                 int(data.pickup_required), int(data.dropoff_required),
                 iso(data.pickup_at), iso(data.dropoff_at), data.transportation_notes),
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
            pickup = values.get("pickup_at")
            if pickup is None and before["pickup_at"]:
                pickup = datetime.fromisoformat(before["pickup_at"])
            dropoff = values.get("dropoff_at")
            if dropoff is None and before["dropoff_at"]:
                dropoff = datetime.fromisoformat(before["dropoff_at"])
            if pickup and (pickup.tzinfo is None or pickup > start):
                raise ValueError("pickup_at must be timezone-aware and not after start_at")
            if dropoff and (dropoff.tzinfo is None or (end and dropoff < end)):
                raise ValueError("dropoff_at must be timezone-aware and not before end_at")
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

    def list_parent_availability(self, family_id, parent_id=None):
        clauses, params = ["family_id=?"], [family_id]
        if parent_id:
            clauses.append("parent_id=?")
            params.append(parent_id)
        with self.connect() as db:
            rows = db.execute(
                f"SELECT * FROM availability_rules WHERE {' AND '.join(clauses)} "
                "ORDER BY parent_id, day_of_week, unavailable_start",
                params,
            ).fetchall()
        return [AvailabilityRule.model_validate(dict(row)) for row in rows]

    def check_parent_availability(self, family_id, parent_id, start_at, end_at):
        if start_at.tzinfo is None or end_at.tzinfo is None:
            raise ValueError("availability times must be timezone-aware")
        if end_at <= start_at:
            raise ValueError("end_at must be later than start_at")
        conflicts = []
        for rule in self.list_parent_availability(family_id, parent_id):
            zone = ZoneInfo(rule.timezone)
            local_start, local_end = start_at.astimezone(zone), end_at.astimezone(zone)
            current = local_start.date()
            while current <= local_end.date():
                active = (
                    current.weekday() == rule.day_of_week
                    and (rule.effective_start is None or current >= rule.effective_start)
                    and (rule.effective_end is None or current <= rule.effective_end)
                )
                if active:
                    blocked_start = datetime.combine(current, rule.unavailable_start, zone)
                    blocked_end = datetime.combine(current, rule.unavailable_end, zone)
                    if local_start < blocked_end and local_end > blocked_start:
                        conflicts.append({
                            "kind": "parent_unavailable",
                            "parent_id": parent_id,
                            "start_at": blocked_start.isoformat(),
                            "end_at": blocked_end.isoformat(),
                            "reason": rule.reason,
                            "rule_id": rule.id,
                        })
                current += timedelta(days=1)
        return conflicts

    @staticmethod
    def _event_interval(event):
        start = datetime.fromisoformat(event["start_at"])
        end = datetime.fromisoformat(event["end_at"]) if event["end_at"] else start
        return start, end

    def transportation_requirements(self, events):
        requirements = []
        for event in events:
            start, end = self._event_interval(event)
            common = {
                "event_id": event["id"], "event_version": event["version"],
                "child_id": event["child_id"], "location": event["location"],
            }
            if event["pickup_required"]:
                at = datetime.fromisoformat(event["pickup_at"]) if event["pickup_at"] else start
                requirements.append({**common, "requirement_id": f"{event['id']}:pickup",
                    "requirement_type": "pickup", "required_start": (at-timedelta(minutes=15)).isoformat(),
                    "required_end": at.isoformat()})
            if event["dropoff_required"]:
                at = datetime.fromisoformat(event["dropoff_at"]) if event["dropoff_at"] else end
                requirements.append({**common, "requirement_id": f"{event['id']}:dropoff",
                    "requirement_type": "dropoff", "required_start": at.isoformat(),
                    "required_end": (at+timedelta(minutes=15)).isoformat()})
        return requirements

    def check_transportation_conflicts(self, family_id, assignments, travel_buffer_minutes=20):
        by_parent = {}
        conflicts, warnings = [], []
        for item in assignments:
            parent = item.get("assigned_parent_id")
            if not parent:
                conflicts.append({"kind": "unassigned_transportation", **item})
                continue
            start = datetime.fromisoformat(item["required_start"])
            end = datetime.fromisoformat(item["required_end"])
            conflicts.extend(self.check_parent_availability(family_id, parent, start, end))
            by_parent.setdefault(parent, []).append((start, end, item))
            if not item.get("location"):
                warnings.append({"kind": "unknown_location", "requirement_id": item["requirement_id"]})
        buffer = timedelta(minutes=travel_buffer_minutes)
        for parent, legs in by_parent.items():
            legs.sort(key=lambda leg: leg[0])
            for previous, current in zip(legs, legs[1:]):
                if current[0] < previous[1]:
                    conflicts.append({"kind": "transportation_overlap", "parent_id": parent,
                        "requirements": [previous[2]["requirement_id"], current[2]["requirement_id"]]})
                elif (previous[2].get("location") != current[2].get("location")
                      and current[0] < previous[1] + buffer):
                    conflicts.append({"kind": "insufficient_travel_time", "parent_id": parent,
                        "required_minutes": travel_buffer_minutes,
                        "requirements": [previous[2]["requirement_id"], current[2]["requirement_id"]]})
        return {"conflicts": conflicts, "warnings": warnings}

    def generate_schedule_candidates(self, family_id, event_ids, parent_ids, candidate_count=3):
        if not event_ids or not parent_ids:
            raise ValueError("event_ids and parent_ids are required")
        if len(event_ids) > 8 or len(parent_ids) > 4:
            raise ValueError("candidate generation supports at most 8 events and 4 parents")
        with self.connect() as db:
            rows = [dict(self.get_row(db, family_id, event_id)) for event_id in event_ids]
        if any(row["status"] != "active" for row in rows):
            raise ValueError("candidate events must be active")
        fingerprint_source = "|".join(f"{r['id']}:{r['version']}" for r in sorted(rows, key=lambda r:r["id"]))
        fingerprint = sha256(fingerprint_source.encode()).hexdigest()[:16]
        candidates = []
        for index, parents in enumerate(product(parent_ids, repeat=len(rows)), start=1):
            conflicts, warnings, rationale, transport = [], [], [], []
            assignments = []
            coverage = []
            for row, parent in zip(rows, parents):
                assignments.append(CandidateAssignment(
                    event_id=row["id"], expected_version=row["version"], assigned_parent_id=parent
                ))
                start, end = self._event_interval(row)
                for unavailable in self.check_parent_availability(family_id, parent, start, end):
                    conflicts.append({**unavailable, "event_id": row["id"]})
                coverage.append({"requirement_id": f"{row['id']}:coverage", "event_id": row["id"],
                    "event_version": row["version"], "requirement_type": "event_coverage",
                    "required_start": start.isoformat(), "required_end": end.isoformat(),
                    "location": row["location"], "assigned_parent_id": parent})
                for requirement in self.transportation_requirements([row]):
                    leg = {**requirement, "assigned_parent_id": parent}
                    transport.append(leg)
                    coverage.append(leg)
            checked = self.check_transportation_conflicts(family_id, coverage)
            conflicts.extend(checked["conflicts"])
            warnings.extend(checked["warnings"])
            counts = {parent: parents.count(parent) for parent in parent_ids}
            imbalance = max(counts.values()) - min(counts.values())
            score = 10 * len(rows) - 10 * len(conflicts) - 2 * len(warnings) - imbalance
            rationale.append(f"Covers {len(rows)} events across {len(set(parents))} parent(s).")
            if imbalance == 0:
                rationale.append("Responsibilities are evenly balanced.")
            candidates.append(ScheduleCandidate(
                candidate_id=f"option-{index}", assignments=assignments,
                transportation=transport, conflicts=conflicts, warnings=warnings,
                score=score, rationale=rationale,
            ))
        candidates.sort(key=lambda c: (-c.score, len(c.conflicts), c.candidate_id))
        selected = candidates[:max(1, min(candidate_count, 5))]
        recommended = next((c.candidate_id for c in selected if not c.conflicts), None)
        return CandidateSet(
            family_id=family_id, generated_at=datetime.now(timezone.utc),
            calendar_fingerprint=fingerprint, candidates=selected,
            recommended_candidate_id=recommended,
        )

    def review_schedule_candidate(self, family_id, candidate):
        assignments = candidate.get("assignments") or []
        if not assignments:
            raise ValueError("candidate assignments are required")
        conflicts = list(candidate.get("conflicts") or [])
        warnings = list(candidate.get("warnings") or [])
        rows, coverage = [], []
        with self.connect() as db:
            for assignment in assignments:
                row = dict(self.get_row(db, family_id, assignment["event_id"]))
                rows.append(row)
                if row["status"] != "active":
                    conflicts.append({"kind": "inactive_event", "event_id": row["id"]})
                if row["version"] != assignment.get("expected_version"):
                    conflicts.append({
                        "kind": "stale_event_version", "event_id": row["id"],
                        "expected_version": assignment.get("expected_version"),
                        "current_version": row["version"],
                    })
                start, end = self._event_interval(row)
                parent = assignment.get("assigned_parent_id")
                coverage.append({
                    "requirement_id": f"{row['id']}:coverage", "event_id": row["id"],
                    "event_version": row["version"], "requirement_type": "event_coverage",
                    "required_start": start.isoformat(), "required_end": end.isoformat(),
                    "location": row["location"], "assigned_parent_id": parent,
                })
                for requirement in self.transportation_requirements([row]):
                    coverage.append({**requirement, "assigned_parent_id": parent})
        checked = self.check_transportation_conflicts(family_id, coverage)
        conflicts.extend(checked["conflicts"])
        warnings.extend(checked["warnings"])
        fingerprint_source = "|".join(
            f"{row['id']}:{row['version']}" for row in sorted(rows, key=lambda row: row["id"])
        )
        return {
            "status": "approved" if not conflicts else "revision_required",
            "reviewed_candidate_id": candidate.get("candidate_id"),
            "calendar_fingerprint": sha256(fingerprint_source.encode()).hexdigest()[:16],
            "blocking_conflicts": conflicts,
            "warnings": warnings,
            "reviewed_revision_number": candidate.get("revision_number", 1),
            "event_ids": [row["id"] for row in rows],
        }
