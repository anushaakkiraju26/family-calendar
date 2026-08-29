---
name: family-preferences
description: How to use stored household preferences without inventing personal data.
---

# Family preferences

- Family timezone: Pacific Time, using the IANA timezone
  `America/Los_Angeles` so PST/PDT daylight-saving changes are handled
  automatically.
- School hours: 9:00 AM to 3:00 PM, Monday through Friday.
- School calendar source: the reviewed Reed Elementary 2026-2027 calendar in
  `data/reed_elementary_2026_2027.json`.
- Treat activities overlapping school hours on school days as potential
  conflicts unless the parent explicitly says the activity is school-related.
- Quiet hours: 9:00 PM to 7:00 AM Monday through Friday, and 10:00 PM to
  8:00 AM on weekends.
- Default reminder recipients: both parents, identified in the MVP as
  `parent-1` and `parent-2`.
- Vikram is unavailable Tuesday through Thursday from 9:30 AM to 4:00 PM
  Pacific Time for children's event pickup or drop-off. Treat any overlapping
  transportation assignment to Vikram as a blocking conflict and propose a
  different parent or a time outside that window. Match the parent name
  case-insensitively and normalize it to the parent ID `vikram` when a tool
  requires an identifier.
- Default day-of reminder: 8:00 AM Pacific Time by SMS.
- A parent-provided recipient, channel, or reminder time overrides these defaults.
- Read /memories/family_preferences.md when it exists.
- Preferences may provide timezone, quiet hours, default reminder recipients,
  transportation patterns, and preferred reminder times.
- Explicit instructions in the current request override stored preferences.
- Ask rather than invent a missing family member, child, phone, or preference.
