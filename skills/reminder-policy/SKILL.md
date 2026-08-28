---
name: reminder-policy
description: Rules for creating and cancelling family event reminders.
---

# Reminder policy

- Resolve the exact active event before scheduling a reminder.
- Scheduling and cancelling reminders require parent approval.
- Use each parent's requested channel and reminder time.
- Draft a concise message containing the child, activity, local date and time,
  and location when known, and save it as `message_body`.
- When a parent requests a day-of reminder for both parents without more
  detail, use `schedule_day_of_reminders` with recipients `parent-1` and
  `parent-2`, SMS, and 8:00 AM America/Los_Angeles.
- Respect quiet hours when family preferences provide them.
- Never claim that a scheduled reminder has already been delivered.
- This MVP stores reminder drafts only. Never claim that parents will receive a
  message or that an SMS delivery worker exists.
- A deleted event cannot receive new reminders.
