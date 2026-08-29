# Family Activity Deep Agent

A Deep Agents coordinator with specialist sub-agents and a standalone MCP
server for a shared family calendar.

## Agent architecture

- Family Coordinator plans work and delegates through task
- Intake Agent normalizes parent requests into shared JSON state
- Calendar Agent manages event creation, updates, deletion, and restoration
- Conflict Agent checks child, assigned-parent, school-hour, and dated school-calendar overlaps
- Weekly Planner combines family events, school dates, and parent assignments
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
2. Weekly Planner loads family events and the Reed Elementary calendar.
3. Conflict checks cover children, assigned parents, regular school hours,
   timed school events, closures, and early dismissals.
4. Schedule Reviewer audits the complete proposal.
5. A plan with blocking findings returns to the Weekly Planner for revision and
   is reviewed again.
6. Reminder Agent drafts day-of reminder records for an approved proposal.
7. Proposed mutations are presented together for human review. Independent
   tool calls are emitted together so LangGraph can show a grouped approval set.

Shared artifacts for this workflow are `/work/weekly_schedule.json`,
`/work/assignment_proposal.json`, `/reviews/weekly_schedule_review.json`, and
`/work/reminder_plan.json`. These files coordinate the run; SQLite remains the
durable source of truth.

Example:

    family-activity-agent "Coordinate next week for family-1, identify conflicts, propose parent assignments, and draft day-of reminders"

## School calendar

`data/reed_elementary_2026_2027.json` is a reviewed transcription of the
attached Reed Elementary School 2026–2027 calendar. The original calendar says
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
- schedule_reminder
- schedule_day_of_reminders
- list_reminders
- cancel_reminders

SQLite is used for the first working version. CalendarRepository isolates
database access so PostgreSQL can replace it later.
Same-child and same-parent overlaps are rejected transactionally by the
repository during event creation and schedule-related updates. The agent's
conflict check improves the explanation but is not the enforcement boundary.

## Setup

    cd /Users/anushaakkiraju/family-activity-agent
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e '.[dev]'
    pytest

Copy .env.example to .env and add a Groq API key from the Groq Console.

    GROQ_API_KEY=your-groq-key
    FAMILY_ACTIVITY_MODEL=openai/gpt-oss-20b

## Run the Deep Agent

    family-activity-agent "Add soccer practice tomorrow from 4 to 5 PM for family-1"

The CLI prints each pending mutation and asks for approval before it runs.
Rate limits, timeouts, connection failures, and tool/database errors are shown
as concise messages instead of raw tracebacks. Use `--debug` during development
when a traceback is needed. After any failure that follows an approval, inspect
the calendar before retrying because the approved tool call may have completed.

## Reminder MVP scope

Reminder tools draft and store message text, recipients, channel, and scheduled
time. They do not send SMS messages. Actual delivery through Twilio and a
background worker is future work; agent responses must describe reminders as
saved drafts rather than sent or guaranteed deliveries.

## Run only the MCP server

Start Streamable HTTP for an external MCP client:

    family-activity-mcp --transport streamable-http

The default MCP endpoint is http://127.0.0.1:8000/mcp.

Start stdio for clients that launch the process locally:

    family-activity-mcp --transport stdio

Set FAMILY_ACTIVITY_DB to override the SQLite database location.

## Security note

For this local course scaffold, tools accept family_id. Before production,
derive it from authenticated identity and require server-issued confirmation
tokens for destructive and notification-related operations.

## Evaluations

Run `pytest` for the offline evaluation suite. It uses a deterministic fake chat
model for real Deep Agent + LangGraph + MCP + SQLite integration tests, so it
does not consume Groq quota. `evaluations/cases.json` contains the live/manual
prompt matrix, expected tools, approval points, outcomes, and failure cases used
for the course demo.

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
results. Use synthetic family names and activities for course demonstrations;
do not trace real children's names, schedules, phone numbers, or other private
family data. Leave `LANGSMITH_TRACING=false` for ordinary private use.
