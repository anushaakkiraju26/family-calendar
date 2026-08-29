---
name: calendar-policy
description: Rules for safely reading and changing the shared family calendar.
---

# Calendar policy

- Search before updating, deleting, or restoring an event.
- If multiple events match, return choices instead of guessing.
- Always use the current event version for updates and deletion.
- Check child and assigned-parent conflicts before creating or moving an event.
- For weekly planning and school-day activities, also call
  `list_school_events` and `check_school_conflicts`.
- Treat timed school-event overlaps as conflicts. Treat closures, early
  dismissals, and untimed school events as planning warnings that require the
  coordinator to explain transportation or supervision impact.
- The supplied Reed Elementary 2026-2027 calendar says dates are subject to
  change; identify it as the source and do not present it as live school data.
- Creating, updating, deleting, and restoring require parent approval.
- Deletion is soft deletion and cancels pending reminders.
- Do not permanently delete records.
- Use timezone-aware ISO 8601 timestamps.
- Do not assume the scope of a recurring-event change.
