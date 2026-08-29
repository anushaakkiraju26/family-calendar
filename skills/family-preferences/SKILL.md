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
- Default day-of reminder: 8:00 AM Pacific Time by SMS.
- A parent-provided recipient, channel, or reminder time overrides these defaults.
- Read /memories/family_preferences.md when it exists.
- Preferences may provide timezone, quiet hours, default reminder recipients,
  transportation patterns, and preferred reminder times.
- Explicit instructions in the current request override stored preferences.
- Ask rather than invent a missing family member, child, phone, or preference.
