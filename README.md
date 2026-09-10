# Family Activity Deep Agent

A Deep Agents coordinator with specialist sub-agents and a standalone MCP
server for a shared family calendar.

## Agent architecture

- Family Coordinator plans work and delegates through task
- Intake Agent normalizes parent requests into shared JSON state
- Calendar Agent manages event creation, updates, deletion, and restoration
- Conflict Agent checks child, assigned-parent, school-hour, and dated school-calendar overlaps
- Weekly Planner combines family events, school dates, and parent assignments
- Transportation Agent generates and ranks parent, pickup, and drop-off options
- Family Outing Agent finds and ranks cited places for weekends and school breaks
- Schedule Reviewer audits the whole weekly plan and requests revision when needed
- Reminder Agent schedules and cancels reminders
- Human approval protects all calendar and reminder mutations

The coordinator launches the MCP server over stdio and discovers its tools
through langchain-mcp-adapters. No second server command is required.

## State and memory boundary

SQLite is the sole durable source of truth for calendar events, reminder
drafts, deletion state, versions, and audit history. Each CLI invocation is an
independent parent request and does not retain conversation history. The
in-memory LangGraph checkpointer exists only to resume human approval within
the running command.

At the start of each invocation, the CLI removes only the known temporary
planning, review, and completion JSON artifacts from the previous run. This
prevents stale agent files from influencing a new request; it never clears the
SQLite calendar database.

## Deep weekly coordination workflow

Simple single-event requests retain a low-latency direct-tool path. A request
to coordinate or review a whole week uses the full multi-agent workflow:

1. Intake Agent normalizes the goal and date range.
2. Weekly Planner loads family events and the Maple Grove Elementary calendar.
3. Transportation Agent loads structured parent availability and generates
   three deterministically scored assignment candidates.
4. Conflict checks cover children, assigned parents, transportation coverage,
   travel buffers, regular school hours,
   timed school events, closures, and early dismissals.
5. Schedule Reviewer audits the recommended candidate and its calendar fingerprint.
6. A plan with blocking findings returns to the Weekly Planner and Transportation
   Agent for revision and
   is reviewed again.
7. Reminder Agent drafts day-of reminder records for an approved proposal.
8. The parent selects an option; its event versions are rechecked before any write.
9. Proposed mutations are presented together for human review. Independent
   tool calls are emitted together so LangGraph can show a grouped approval set.

Shared artifacts for this workflow are `/work/weekly_schedule.json`,
`/work/assignment_proposal.json`, `/reviews/weekly_schedule_review.json`, and
`/work/reminder_plan.json`. Ranked candidates and transportation findings are
stored in `/work/transportation_plan.json`. These files coordinate the run; SQLite remains the
durable source of truth.

Example:

    family-activity-agent "Coordinate next week for family-1, identify conflicts, propose parent assignments, and draft day-of reminders"

Hero workflow:

    family-activity-agent "Coordinate next week for family-1. Check school events, resolve activity and transportation conflicts, generate three schedule options for parent-1, parent-2, and vikram, recommend the best plan, and draft reminders. Do not apply changes until I approve."

For a repeatable demonstration, seed an isolated database and point one
CLI invocation at it:

    python tools/seed_hero_demo.py

Use the exact Monday-Sunday dates printed by the seeder in the request. For
example, when it prints `2026-08-31 through 2026-09-06`:

    FAMILY_ACTIVITY_DB=data/hero_demo.db family-activity-agent "Coordinate August 31 through September 6, 2026 for family-1. Read the existing calendar and school events, resolve activity and transportation conflicts, generate three schedule options for parent-1, parent-2, and vikram, recommend the best plan, and draft reminders. This is planning only; do not apply changes."

The demo database is separate from `data/family_activity.db` and is ignored by
Git. It contains overlapping activities for different children, transportation
requirements at different locations, and a volunteer commitment during
Vikram's structured work unavailability.

The candidate scheduler is deterministic: it uses stored event versions,
parent availability rules, event overlaps, pickup/drop-off requirements, and a
20-minute different-location travel buffer. The LLM explains the alternatives;
it does not invent their scores. Selecting an old option after an event changes
fails through the existing `expected_version` guard.

## Family outing research

The Family Outing Agent first checks the family and Maple Grove Elementary calendars,
then uses You.com's hosted MCP server to find current places and events for an
available weekend or school-break window. Search results retain their source
URLs. They remain proposals: the parent must verify hours,
prices, tickets, suitability, and travel time. Selecting an outing does not add
it to the calendar; a separate `create_event` call still requires approval.
Third-party pages may be used for discovery, but each final option must cite an
official venue, park-agency, or government page retrieved with `you-contents`.
The agent does not claim a numeric drive time without current mapping evidence.
Although the hosted connection exposes seven You.com tools, the outing
specialist receives only the controlled `research_family_outings` wrapper. The
wrapper checks both calendars and uses `you-search` plus `you-contents`; the
remaining hosted tools are not exposed to the specialist.

Example:

    family-activity-agent "Find three science or outdoor activities near San Jose for family-1 this weekend. Check our calendar first and stay within a 45-minute drive."

## Seeded month and Kinday frontend

Populate the local `family-1` SQLite calendar with the idempotent 21-event demo
month used for scheduling and transportation tests:

    python tools/seed_month_demo.py --database data/family_activity.db --start 2026-08-29

The generated range is August 30 through September 29, 2026. It includes
recurring practices, simultaneous activities for two children, school-hour
appointments, parent assignments, and pickup/drop-off requirements. Re-running
the command does not create duplicates.

The [`frontend/`](frontend/) directory is the Kinday calendar UI: a Next.js
prototype seeded with a static snapshot of the same demo month, used to
visualize what the agent's weekly plan looks like to a parent. See
[frontend/README.md](frontend/README.md) for what it is and how to run it. It
is a UI prototype, not a live client of the CLI/MCP backend: it holds its own
copy of the data in the browser (`localStorage`) and does not read or write
`data/family_activity.db`. Local calendar mutations made through the CLI
remain authoritative there regardless of what the frontend shows.

## School calendar

`data/maple_grove_elementary_2026_2027.json` is a reviewed transcription of the
attached Maple Grove Elementary School 2026–2027 calendar. The original calendar says
all dates are subject to change. The agent therefore identifies this file as
its source and does not describe it as live school data.

The school-calendar tools are read-only:

- `list_school_events`
- `check_school_conflicts`

## Tools

- create_event
- list_events
- update_event
- delete_event (soft deletion)
- restore_event
- check_conflicts
- list_school_events
- check_school_conflicts
- list_parent_availability
- check_parent_availability
- check_transportation_conflicts
- generate_schedule_candidates
- review_schedule_candidate
- check_outing_time_window
- you-search (hosted You.com MCP)
- you-contents (hosted You.com MCP)
- you-research (hosted You.com MCP)
- you-answer (hosted You.com MCP)
- you-finance (hosted You.com MCP)
- you-balance (hosted You.com MCP)
- you-discover (hosted You.com MCP)
- schedule_reminder
- schedule_day_of_reminders
- list_reminders
- cancel_reminders

SQLite is used for the first working version. CalendarRepository isolates
database access so PostgreSQL can replace it later.
Same-child and same-parent overlaps are rejected transactionally by the
repository during event creation and schedule-related updates. The agent's
conflict check improves the explanation but is not the enforcement boundary.
Vikram's Tuesday-through-Thursday 9:30 AM-4:00 PM unavailability is also stored
as structured SQLite rules so candidate generation enforces it independently
of model reasoning.

## Setup

    git clone https://github.com/anushaakkiraju26/family-activity-agent.git
    cd family-activity-agent
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e '.[dev]'
    pytest

Copy `.env.example` to `.env` and add a Nebius Token Factory API key. Add a
You.com API key only when you want live family-outing research.

    NEBIUS_API_KEY=your-nebius-key
    NEBIUS_BASE_URL=https://api.tokenfactory.us-central1.nebius.com/v1/
    FAMILY_ACTIVITY_MODEL=nvidia/Nemotron-3-Nano-Omni
    YDC_API_KEY=your-you-com-key
    YDC_MCP_URL=https://api.you.com/mcp?tools=you-search,you-contents,you-research,you-answer,you-finance,you-balance,you-discover

## Run the Deep Agent

    family-activity-agent "Add soccer practice tomorrow from 4 to 5 PM for family-1"

The CLI prints each pending mutation and asks for approval before it runs.
Rate limits, timeouts, connection failures, and tool/database errors are shown
as concise messages instead of raw tracebacks. Use `--debug` during development
when a traceback is needed. After any failure that follows an approval, inspect
the calendar before retrying because the approved tool call may have completed.

## Reminder MVP scope

Reminder tools draft and store message text, recipients, channel, and scheduled
time. You can set up text (SMS) or WhatsApp to actually send these reminders —
that delivery integration (e.g., Twilio and a background worker) isn't included
yet, so currently the project only drafts messages; agent responses describe
reminders as saved drafts rather than sent or guaranteed deliveries.

## Run only the MCP server

Start Streamable HTTP for an external MCP client:

    family-activity-mcp --transport streamable-http

The default MCP endpoint is http://127.0.0.1:8000/mcp.

Start stdio for clients that launch the process locally:

    family-activity-mcp --transport stdio

Set FAMILY_ACTIVITY_DB to override the SQLite database location.

## Security note

For this local scaffold, tools accept family_id. Before production,
derive it from authenticated identity and require server-issued confirmation
tokens for destructive and notification-related operations.

## Evaluations

Run `pytest` for the offline evaluation suite. It uses a deterministic fake chat
model for real Deep Agent + LangGraph + MCP + SQLite integration tests, so it
does not consume Nebius quota. `evaluations/cases.json` contains the live/manual
prompt matrix, expected tools, approval points, outcomes, and failure cases used
for the demo.

## Optional LangSmith tracing

LangSmith tracing is opt-in. Create a LangSmith API key and add the following
to `.env` when you want to capture a live demo trace:

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your-langsmith-key
LANGSMITH_PROJECT=family-activity-agent-mvp
```

Then run the CLI normally. The root trace is named
`family-activity-cli-request` and includes tags for the application, CLI
surface, and MVP, plus non-sensitive model and reminder-mode metadata. The CLI
waits for background traces before exiting.

LangSmith traces may contain prompts, model responses, tool arguments, and tool
results. Use synthetic family names and activities for demonstrations;
do not trace real children's names, schedules, phone numbers, or other private
family data. Leave `LANGSMITH_TRACING=false` for ordinary private use.
