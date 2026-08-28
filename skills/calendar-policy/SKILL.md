---
name: calendar-policy
description: Rules for safely reading and changing the shared family calendar.
---

# Calendar policy

- Search before updating, deleting, or restoring an event.
- If multiple events match, return choices instead of guessing.
- Always use the current event version for updates and deletion.
- Check child and assigned-parent conflicts before creating or moving an event.
- Creating, updating, deleting, and restoring require parent approval.
- Deletion is soft deletion and cancels pending reminders.
- Do not permanently delete records.
- Use timezone-aware ISO 8601 timestamps.
- Do not assume the scope of a recurring-event change.
