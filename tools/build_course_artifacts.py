from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DOCX_PATH = DOCS / "Family_Activity_Deep_Agent_Project_Documentation.docx"
NOTEBOOK_PATH = ROOT / "family_activity_deep_agent.ipynb"
IMAGES = ROOT / "images"


def set_run_font(run, size=11, bold=False, color="000000", name="Arial"):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor.from_string(color)
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)


def set_cell_margins(cell, top=80, start=120, bottom=80, end=120):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for edge, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        element = tc_mar.find(qn(f"w:{edge}"))
        if element is None:
            element = OxmlElement(f"w:{edge}")
            tc_mar.append(element)
        element.set(qn("w:w"), str(value))
        element.set(qn("w:type"), "dxa")


def set_table_borders(table, color="DADCE0", size="4"):
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = borders.find(qn(f"w:{edge}"))
        if tag is None:
            tag = OxmlElement(f"w:{edge}")
            borders.append(tag)
        tag.set(qn("w:val"), "single")
        tag.set(qn("w:sz"), size)
        tag.set(qn("w:color"), color)


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    header = OxmlElement("w:tblHeader")
    header.set(qn("w:val"), "true")
    tr_pr.append(header)


def configure_styles(doc):
    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(11)
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
    normal.paragraph_format.space_after = Pt(8)
    normal.paragraph_format.line_spacing = 1.15

    for name, size, color, before, after in (
        ("Heading 1", 20, "000000", 20, 6),
        ("Heading 2", 16, "000000", 18, 6),
        ("Heading 3", 14, "434343", 16, 4),
    ):
        style = doc.styles[name]
        style.font.name = "Arial"
        style.font.size = Pt(size)
        style.font.bold = False
        style.font.color.rgb = RGBColor.from_string(color)
        style._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True

    for name in ("List Bullet", "List Number"):
        style = doc.styles[name]
        style.font.name = "Arial"
        style.font.size = Pt(11)
        style.paragraph_format.left_indent = Inches(0.5)
        style.paragraph_format.first_line_indent = Inches(-0.25)
        style.paragraph_format.space_after = Pt(4)
        style.paragraph_format.line_spacing = 1.15


def add_title(doc):
    title = doc.add_paragraph()
    title.paragraph_format.space_before = Pt(0)
    title.paragraph_format.space_after = Pt(3)
    set_run_font(title.add_run("Family Activity Deep Agent"), size=26)

    subtitle = doc.add_paragraph()
    subtitle.paragraph_format.space_after = Pt(16)
    set_run_font(subtitle.add_run("Week 3 Project — Solution Documentation (Code Track)"), size=12, color="555555")

    summary = doc.add_paragraph()
    set_run_font(summary.add_run("Implementation status: "), bold=True)
    set_run_font(summary.add_run("Working CLI MVP with Deep Agents, LangGraph, Nebius Nemotron, MCP tools, SQLite persistence, human approval, deterministic validation, offline evaluations, and optional LangSmith tracing."))


def add_bullets(doc, items):
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        set_run_font(p.add_run(item))


def add_numbered(doc, items):
    for item in items:
        p = doc.add_paragraph(style="List Number")
        set_run_font(p.add_run(item))


def add_table(doc, headers, rows, widths):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table.autofit = False
    table.allow_autofit = False
    set_table_borders(table)
    set_repeat_table_header(table.rows[0])
    for i, header in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.width = Inches(widths[i])
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        set_cell_margins(cell)
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        set_run_font(p.add_run(header), bold=True)
    for row in rows:
        cells = table.add_row().cells
        for i, value in enumerate(row):
            cells[i].width = Inches(widths[i])
            cells[i].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cells[i])
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            set_run_font(p.add_run(str(value)), size=10)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return table


def add_code_block(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.right_indent = Inches(0.25)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.line_spacing = 1.0
    p_pr = p._p.get_or_add_pPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), "F8F9FA")
    p_pr.append(shading)
    set_run_font(p.add_run(text), size=9, name="Courier New")


def build_docx():
    DOCS.mkdir(parents=True, exist_ok=True)
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.right_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)
    configure_styles(doc)
    add_title(doc)

    doc.add_heading("1. Executive Summary", level=1)
    doc.add_paragraph(
        "This project implements a family activity coordination agent for parents. It accepts natural-language calendar requests through a command-line interface, resolves dates in the family timezone, delegates complex work to specialist subagents, calls a standalone MCP calendar server, stores durable state in SQLite, detects scheduling conflicts, and pauses for human approval before every write action. The MVP drafts and stores reminder messages; it intentionally does not send SMS messages."
    )

    doc.add_heading("2. Problem Statement", level=1)
    doc.add_paragraph(
        "Parents often coordinate school assignments, volunteering, practices, appointments, birthdays, and reminders across chats, paper notes, and separate calendars. Information is easy to miss, both parents may assume the other is handling an activity, and overlapping transportation responsibilities may not be noticed until the last minute. The Family Activity Deep Agent provides one conversational entry point backed by a shared, auditable calendar."
    )

    doc.add_heading("3. Agent One-Liner", level=1)
    doc.add_paragraph(
        "My agent helps parents coordinate family activities and discover cited family outings through a CLI-backed shared calendar. It autonomously reads family and school-calendar state, generates ranked transportation-aware weekly options, searches current web evidence for free weekends and school breaks, reviews plans, checks conflicts, and drafts reminders using 25 MCP tools across a local family server and hosted You.com server; it hands off to a parent before every calendar or reminder change."
    )

    doc.add_heading("4. Scope", level=1)
    doc.add_heading("In scope", level=2)
    add_bullets(doc, [
        "Create, list, update, soft-delete, and restore family events.",
        "Track a child, assigned parent, location, start/end time, status, and version.",
        "Detect same-child and same-parent overlaps deterministically.",
        "Use America/Los_Angeles and resolve today/tomorrow from current Pacific time.",
        "Draft and store day-of reminders for one or both parents.",
        "Require approval before all calendar and reminder mutations.",
        "Persist calendar data, reminder drafts, and audit history in SQLite.",
        "Provide offline automated evaluations and optional LangSmith tracing.",
    ])
    doc.add_heading("Out of scope", level=2)
    add_bullets(doc, [
        "Actual SMS delivery through Twilio or another messaging provider.",
        "Live synchronization between the separate Kinday frontend snapshot and SQLite.",
        "Authentication, production tenant identity, and phone-number management.",
        "Calendar synchronization with Google Calendar or Apple Calendar.",
        "Recurring-event series editing and live traffic-aware route optimization.",
    ])

    doc.add_heading("5. High-Level Architecture", level=1)
    doc.add_paragraph("The coordinator owns the conversation and approval boundary. Specialist agents share temporary files, while all durable calendar state passes through MCP tools into SQLite.")
    add_code_block(doc, """Parent CLI
    │
    ▼
Family Coordinator (Deep Agents + LangGraph)
    ├── Intake Agent ───── normalizes ambiguous requests
    ├── Calendar Agent ─── event lifecycle
    ├── Conflict Agent ─── overlap analysis
    ├── Weekly Planner ─── weekly context
    ├── Transportation ─── ranked assignment candidates
    ├── Family Outing ──── cited weekend and school-break ideas
    ├── Schedule Reviewer  independent review
    └── Reminder Agent ─── reminder drafts
              │
              ▼
      MCP Tool Server (stdio)
              │
       ┌──────┴────────┐
       ▼               ▼
CalendarRepository   18 local tools
You.com MCP Server    7 hosted tools
       │
       ▼
SQLite: events + reminders + availability_rules + audit_logs""")

    doc.add_heading("6. Runtime Flow", level=1)
    add_numbered(doc, [
        "The CLI loads environment configuration, clears only stale temporary agent artifacts, and creates a new request thread.",
        "The coordinator resolves intent, Pacific timezone, relative dates, child identifiers, and family scope.",
        "Simple requests use MCP tools directly; complex requests may be delegated to a specialist subagent.",
        "Read tools run autonomously. Repository code validates future dates, versions, family scope, and conflicts.",
        "A write tool causes a LangGraph interrupt and the CLI displays the exact tool name and arguments.",
        "The parent approves or rejects. Only an approved tool call can change SQLite.",
        "The agent summarizes the returned tool result. A plan file never counts as completed work.",
    ])

    doc.add_heading("7. Agent and Subagent Design", level=1)
    add_table(doc, ["Component", "Responsibility", "Tools / state"], [
        ["Family Coordinator", "Plans, routes, handles simple requests, and summarizes verified results.", "All MCP tools; HITL interrupts"],
        ["Intake Agent", "Normalizes ambiguous or multi-activity requests.", "Temporary event_request.json"],
        ["Calendar Agent", "Handles complex searches and event lifecycle operations.", "Calendar tools + calendar policy"],
        ["Conflict Agent", "Explains child and parent overlaps without mutating state.", "check_conflicts"],
        ["Weekly Planner", "Combines family events, Reed school dates, and proposed parent assignments.", "Read-only calendar and school tools"],
        ["Transportation Agent", "Generates ranked assignment and pickup/drop-off candidates.", "Availability, transportation, and candidate tools"],
        ["Family Outing Agent", "Checks free time, searches current sources, and ranks outing ideas.", "Calendar, school, and You.com tools"],
        ["Schedule Reviewer", "Audits a weekly plan and requires revision when blocking issues remain.", "Shared plan and review artifacts"],
        ["Reminder Agent", "Resolves events and creates reviewable reminder drafts.", "Reminder tools + reminder policy"],
    ], [1.35, 3.15, 2.0])

    doc.add_heading("8. MCP Tool Inventory", level=1)
    add_table(doc, ["Tool", "Mode", "Purpose", "Approval"], [
        ["create_event", "Write", "Create a future event with idempotency.", "Required"],
        ["list_events", "Read", "Find active or deleted events by family/time/child.", "No"],
        ["update_event", "Write", "Change an event using expected_version.", "Required"],
        ["delete_event", "Write", "Soft-delete and cancel scheduled reminders.", "Required"],
        ["restore_event", "Write", "Restore a soft-deleted event.", "Required"],
        ["check_conflicts", "Read", "Explain overlapping child/parent activities.", "No"],
        ["list_school_events", "Read", "List Reed Elementary dates in a range.", "No"],
        ["check_school_conflicts", "Read", "Check school hours, closures, early dismissal, and timed events.", "No"],
        ["list_parent_availability", "Read", "List structured parent unavailability rules.", "No"],
        ["check_parent_availability", "Read", "Validate a proposed responsibility against availability.", "No"],
        ["check_transportation_conflicts", "Read", "Check coverage, overlaps, and travel buffers.", "No"],
        ["generate_schedule_candidates", "Read", "Generate and rank versioned weekly assignment options.", "No"],
        ["review_schedule_candidate", "Read", "Deterministically review dates, versions, assignments, and school overlaps.", "No"],
        ["check_outing_time_window", "Read", "Check an outing window against family and school commitments.", "No"],
        ["you-search", "Read / hosted", "Search current web and news results.", "No"],
        ["you-contents", "Read / hosted", "Extract page content from selected URLs.", "No"],
        ["you-research", "Read / hosted", "Run deeper citation-backed multi-source research.", "No"],
        ["you-answer", "Read / hosted", "Return a concise cited answer.", "No"],
        ["you-finance", "Read / hosted", "Research finance topics when explicitly relevant.", "No"],
        ["you-balance", "Read / hosted", "Check remaining You.com API credits.", "No"],
        ["you-discover", "Read / hosted", "Find an appropriate You.com integration path.", "No"],
        ["schedule_reminder", "Write", "Store one reminder draft.", "Required"],
        ["schedule_day_of_reminders", "Write", "Atomically store drafts for both parents.", "Required"],
        ["list_reminders", "Read", "Review reminder drafts and statuses.", "No"],
        ["cancel_reminders", "Write", "Cancel pending drafts for an event.", "Required"],
    ], [1.7, 0.65, 3.15, 1.0])

    doc.add_heading("9. Data and Persistence", level=1)
    doc.add_paragraph("No external dataset is required. The application uses synthetic course-demo family data stored in four SQLite tables.")
    add_table(doc, ["Table", "Durable information"], [
        ["events", "Family-scoped event details, assigned child/parent, status, version, idempotency key, deletion metadata."],
        ["reminders", "Recipient, scheduled time, channel, drafted message body, and status."],
        ["audit_logs", "Action, entity, before/after JSON state, family scope, and timestamp."],
    ], [1.35, 5.15])
    doc.add_paragraph("SQLite is the sole durable source of truth. Conversation history is intentionally not retained between CLI commands. In-memory graph state exists only long enough to resume approvals in the current process.")

    doc.add_heading("10. Prompt and Skill Design", level=1)
    doc.add_paragraph("The coordinator prompt defines routing, timezone defaults, approval rules, completion evidence, and the fast path. Focused subagent prompts restrict each specialist to its responsibility. Skills provide progressively disclosed policies for calendar safety, reminders, and family preferences.")
    add_bullets(doc, [
        "Never invent dates, people, locations, or event IDs.",
        "A mutation is complete only after its MCP tool returns success.",
        "A plan file is not proof that an event or reminder changed.",
        "Past or timezone-naive event starts fail at the repository boundary.",
        "Reminder responses say draft saved and never claim SMS delivery.",
        "Same-child and same-parent overlaps are enforced in code, not only prompts.",
    ])

    doc.add_heading("11. Human-in-the-Loop Boundary", level=1)
    doc.add_paragraph("Read operations are autonomous. The following actions always pause before execution: create, update, delete, restore, schedule reminder drafts, and cancel reminders. The CLI prints exact arguments and accepts approval or rejection feedback. No approval means no write.")
    add_code_block(doc, """READ REQUEST → tool executes → result displayed

WRITE REQUEST → proposed tool call → PENDING APPROVAL
              ├── approve → execute → verify result
              └── reject  → no mutation → acknowledge feedback""")

    doc.add_heading("12. Deterministic Safety and Failure Handling", level=1)
    add_table(doc, ["Failure / risk", "System response"], [
        ["Past or naive event time", "Repository rejects the write with a clear validation error."],
        ["Same child or parent overlap", "Transaction rejects the create/update; agent explains the conflict."],
        ["Stale event version", "Optimistic concurrency check returns the current-version conflict."],
        ["Duplicate retry", "Stable idempotency keys return the existing event or reminder records."],
        ["Nebius 429 / timeout", "CLI returns a concise retry message instead of a traceback."],
        ["MCP or SQLite failure", "No success is assumed; user is told to verify state before retrying."],
        ["Rejected approval", "Pending tool call is not executed."],
        ["Stale agent artifact", "Known temporary JSON files are cleared at the next CLI start."],
    ], [2.0, 4.5])

    doc.add_heading("13. Evaluation Strategy", level=1)
    doc.add_paragraph("The offline suite uses a deterministic fake chat model and does not consume Nebius quota. It verifies repository rules plus the actual Deep Agent, LangGraph interrupt/resume flow, MCP subprocess, and SQLite mutation boundary.")
    add_bullets(doc, [
        "Real MCP read invocation through a managed stdio subprocess.",
        "Mutation absent before approval and present only after resume approval.",
        "Create/list/update/delete/restore lifecycle and family isolation.",
        "Past-event, conflict, reminder, version, and idempotency failure paths.",
        "CLI rate-limit, timeout, connection, database, and unknown-error formatting.",
        "Twenty-one natural-language evaluation cases with expected tools and outcomes.",
    ])

    doc.add_heading("14. Configuration and Runbook", level=1)
    add_code_block(doc, """cd /Users/anushaakkiraju/family-activity-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
# Add NEBIUS_API_KEY. Optionally add LANGSMITH_API_KEY.
pytest
family-activity-agent 'Show activities today for family-1'""")
    doc.add_paragraph("Optional LangSmith tracing uses LANGSMITH_TRACING=true and project family-activity-agent-mvp. Course traces should use synthetic names and schedules because traces can contain prompts and tool results.")

    doc.add_heading("15. Representative Vibe-Coding Prompts and Iterations", level=1)
    add_bullets(doc, [
        "Create a standalone MCP server with event lifecycle and reminder tools; do not reuse the home-buying project.",
        "Build a Deep Agent coordinator with intake, calendar, conflict, and reminder specialists.",
        "Use Nebius Token Factory with Nemotron through its OpenAI-compatible API.",
        "Use Pacific timezone and school hours from family preferences.",
        "Add soft deletion, restoration, both-parent reminder drafts, and approval gates.",
        "Prevent false success when the agent writes a plan but does not execute the MCP tool.",
        "Reject past events and enforce parent/child conflicts deterministically.",
        "Add offline end-to-end evaluations and optional LangSmith tracing.",
    ])
    doc.add_paragraph("Key learning: prompts guide behavior, but high-risk invariants belong in deterministic tools and repository transactions. Tool results—not model prose—must be the evidence for completion.")

    doc.add_heading("16. Demo Script (5 Minutes or Less)", level=1)
    add_numbered(doc, [
        "Show the architecture and identify the coordinator, eight subagents, MCP server, You.com boundary, school calendar, and SQLite state.",
        "Create a future event and pause at the create_event approval prompt; approve it.",
        "List the event to prove persistence in a separate CLI command.",
        "Create a different child's overlapping event to show that it is allowed.",
        "Attempt to assign both overlapping events to one parent and show the conflict with no update.",
        "Draft a day-of reminder for both parents and emphasize that no SMS is sent.",
        "Delete and restore an event to demonstrate reversible writes.",
        "Show the passing pytest suite and one LangSmith trace tree using synthetic data.",
    ])

    doc.add_heading("17. Validation Checklist", level=1)
    add_table(doc, ["Before demo", "During / after demo"], [
        ["Virtual environment active", "Every write displays an approval prompt"],
        ["NEBIUS_API_KEY configured", "Past event is rejected"],
        ["Optional LangSmith key configured", "Parent conflict is detected"],
        ["pytest passes", "Reminder is described as a saved draft"],
        ["Synthetic demo data selected", "Separate CLI read proves SQLite persistence"],
        ["No secrets shown on screen", "Trace and test evidence captured"],
    ], [3.25, 3.25])

    doc.add_heading("18. Current Implementation Boundary and Extensions", level=1)
    add_code_block(doc, """UNDERSTAND REQUEST → READ CALENDAR → CHECK POLICY/CONFLICTS
→ HUMAN APPROVAL FOR WRITE → MCP MUTATION → SQLITE + AUDIT LOG
→ VERIFIED RESPONSE → STOP""")
    doc.add_paragraph("The MVP stops after saving calendar state or reminder drafts. It does not send messages or perform external commitments. A separate hosted Kinday frontend displays a snapshot of the seeded family calendar, but it does not synchronize live with SQLite. Future extensions include Twilio delivery, authenticated family membership, live Kinday synchronization, Google/Apple Calendar synchronization, recurring events, and production PostgreSQL.")

    doc.core_properties.title = "Family Activity Deep Agent — Week 3 Project Documentation"
    doc.core_properties.subject = "Agentic AI Systems course project"
    doc.core_properties.author = "Family Activity Agent Project"
    doc.save(DOCX_PATH)


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": text.splitlines(keepends=True)}


def build_notebook():
    cells = [
        md("""# Family Activity Deep Agent — Shared Calendar & Reminder Drafts

A hands-on tutorial of the **Deep Agents** framework with a standalone **MCP tool server** and durable **SQLite** calendar state.

We build a family coordinator that creates, reads, updates, deletes, and restores activities; detects child and parent conflicts; and stores reviewable reminder drafts.

> **Draft-only messaging.** The MVP stores reminder text but never sends SMS. Every calendar or reminder mutation pauses for parent approval.

This notebook follows the same teaching sequence as the course's GTM Deep Agent example, adapted to the family-calendar use case and the project's real implementation."""),
        md("""## Architecture at a glance

```
Parent request → Family Coordinator (plans, routes, verifies)
                         │
          ┌──────────────┼─────────────────────┐
          ▼              ▼                     ▼
     Calendar work   Weekly planning      Outing research
     + reminders     + review             + cited evidence
          └──────────────┴──────────┬──────────┘
                                ▼
                      Family Activity MCP Server
                                ▼
                  SQLite: events | reminders | audit_logs
```

| Deep Agents concept | Family activity implementation |
|---|---|
| Planning | `write_todos` breaks a parent request into steps |
| Delegation | `task` sends focused work to eight specialists |
| Shared work | Temporary files coordinate one run |
| Tools | 18 local MCP tools; when configured, 7 hosted You.com tools are discovered |
| Skills | Calendar policy, reminder policy, and family preferences load on demand |
| Durable state | SQLite stores events, assignments, reminders, and audit history |
| Human-in-the-loop | LangGraph interrupts before every mutation |
"""),
        md("![Family Activity Deep Agent architecture](./images/01_img.png)\n"),
        md("""## 1. Install and API keys

Run this notebook from the repository root with the project virtual environment. Dependencies are managed by `pyproject.toml`. Never print API keys in notebook output."""),
        code("""# If needed, install the project into the active notebook kernel:
# %pip install -e '.[dev]'
"""),
        code("""import os
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv()
if not os.getenv("NEBIUS_API_KEY"):
    raise RuntimeError("Add NEBIUS_API_KEY to .env before running the live agent cells.")

print("You.com outing search:", "enabled" if os.getenv("YDC_API_KEY") else "disabled")

if os.getenv("LANGSMITH_API_KEY", "").strip():
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ.setdefault("LANGSMITH_PROJECT", "family-activity-agent-mvp")
    print("LangSmith tracing: ENABLED")
else:
    os.environ["LANGSMITH_TRACING"] = "false"
    print("LangSmith tracing: disabled")

print("Model:", os.getenv("FAMILY_ACTIVITY_MODEL", "nvidia/Nemotron-3-Nano-Omni"))
"""),
        md("""## 2. Family grounding

The GTM tutorial grounds its agent in company facts. Here the equivalent grounding is the family's operating context: Pacific Time and school hours. Those facts live in a skill rather than being scattered across user prompts."""),
        code("""preferences = Path("skills/family-preferences/SKILL.md")
print(preferences.read_text())
"""),
        md("""## 3. MCP tools

The Deep Agent launches the local MCP server as a managed stdio subprocess. Tool definitions live in `src/family_activity_mcp/server.py`; validation and SQLite transactions live in `src/family_activity_mcp/repository.py`.

The LLM decides **which** operation is needed. Plain Python enforces facts the model must not improvise: future times, optimistic versions, family scope, idempotency, and overlap rules."""),
        md("![MCP tools](./images/02_img.png)\n"),
        code("""import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from family_activity_agent.agent import mcp_connection

async def discover_tools():
    client = MultiServerMCPClient(mcp_connection())
    return await client.get_tools()

tools = asyncio.run(discover_tools())
for tool in tools:
    print(f"{tool.name}: {tool.description}")
"""),
        md("""## 4. Skills (progressive disclosure)

The coordinator sees skill descriptions first and loads full `SKILL.md` instructions only when relevant. This keeps the always-on prompt smaller while preserving domain policy."""),
        md("![Skills progressive disclosure](./images/03_img.png)\n"),
        code("""for path in sorted(Path("skills").glob("*/SKILL.md")):
    print(f"\\n===== {path} =====")
    print(path.read_text())
"""),
        md("""## 5. Persistence: database + per-run state

The reference tutorial separates files, long-term memory, and a checkpointer. This project makes a deliberate variation:

- **SQLite** is the durable source of truth across CLI sessions.
- **Temporary files** let agents coordinate during one request and are cleared before the next.
- **`InMemorySaver`** holds graph state required to pause and resume an approval in the current process.

No conversational memory is required to remember calendar facts because the tools read them from the database."""),
        md("![Persistence boundary](./images/04_img.png)\n"),
        code("""from family_activity_agent.cli import RUN_ARTIFACTS

print("Durable state: data/family_activity.db")
print("Ephemeral per-run artifacts:")
for artifact in RUN_ARTIFACTS:
    print(" -", artifact)
"""),
        md("""## 6. Specialist subagents

Each specialist has a focused prompt and restricted tool set. The coordinator handles simple requests directly to reduce latency and delegates only when specialization adds value."""),
        md("![Coordinator and specialist agents](./images/05_img.png)\n"),
        code("""from family_activity_agent.prompts import (
    INTAKE_PROMPT, CALENDAR_PROMPT, CONFLICT_PROMPT, OUTING_PROMPT, REMINDER_PROMPT
)

subagents = {
    "intake-agent": "Normalizes ambiguous or multi-activity requests",
    "calendar-agent": "Handles complex event lifecycle operations",
    "conflict-agent": "Explains overlaps without mutating state",
    "weekly-planner": "Builds and revises coordinated weekly plans",
    "transportation-agent": "Ranks assignment and transportation candidates",
    "family-outing-agent": "Finds cited ideas for free weekends and school breaks",
    "schedule-reviewer": "Independently audits the full weekly proposal",
    "reminder-agent": "Creates and manages reminder drafts",
}
for name, purpose in subagents.items():
    print(f"{name}: {purpose}")
"""),
        md("""## 7. Assemble the Deep Agent

This is the core Deep Agents lesson: configure the model, prompt, tools, subagents, skills, backend, checkpointer, and interrupt policy. The framework supplies planning, delegation, filesystem tools, and interrupt plumbing.

`build_family_agent()` also discovers MCP tools and normalizes their results for model tool-message compatibility."""),
        md("![Assembling the Deep Agent](./images/06_img.png)\n"),
        code("""from family_activity_agent.agent import build_family_agent

agent = asyncio.run(build_family_agent())
print("Deep Agent assembled:", agent.name)
"""),
        md("""## 8. Run one family request

We pass one request and let the coordinator plan, call MCP tools, and pause before the write. `recursion_limit` is the hard backstop against runaway loops.

The date is generated seven days ahead so the demonstration never accidentally creates a past event."""),
        md("![Run one family request](./images/07_img.png)\n"),
        code("""from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

demo_day = (datetime.now(ZoneInfo("America/Los_Angeles")) + timedelta(days=7)).date()
run_config = {
    "configurable": {"thread_id": f"notebook-demo-{uuid4()}"},
    "recursion_limit": 30,
    "run_name": "family-activity-notebook-demo",
    "tags": ["family-activity-agent", "notebook", "demo"],
}

request = (
    f"Add Demo Child's soccer practice on {demo_day.isoformat()} "
    "from 4 to 5 PM for family-1"
)
result = asyncio.run(agent.ainvoke(
    {"messages": [{"role": "user", "content": request}]},
    config=run_config,
))
print("Paused for approval:", "__interrupt__" in result)
"""),
        code("""# Inspect the visible coordinator messages and its current TODO plan.
for message in result.get("messages", []):
    message.pretty_print()

print("\\n===== TODOS =====")
for todo in result.get("todos", []):
    print(f"[{todo.get('status')}] {todo.get('content')}")
"""),
        md("![Shared state produced by the run](./images/08_img.png)\n"),
        code("""# Inspect temporary shared artifacts created during this run.
for relative_path in [
    "work/event_request.json",
    "work/calendar_plan.json",
    "work/reminder_plan.json",
    "work/weekly_schedule.json",
    "work/assignment_proposal.json",
    "work/outing_proposal.json",
    "reviews/conflict_report.json",
    "reviews/weekly_schedule_review.json",
    "final/completed_action.json",
]:
    path = Path(relative_path)
    if path.exists():
        print(f"\\n===== /{relative_path} =====\\n{path.read_text()}")
"""),
        md("""## 9. Human-in-the-loop: approve the calendar gate

`interrupt_on` pauses the graph **before** `create_event`. Inspect the exact tool and arguments, then approve, reject with feedback, or edit the arguments. This mirrors the publish gate in the reference project, but protects calendar mutations."""),
        md("![Human approval gate](./images/09_img.png)\n"),
        code("""from family_activity_agent.cli import pending_requests

requests = pending_requests(result)
for pending in requests:
    print("PENDING APPROVAL:", pending)
"""),
        md("""### Approve or reject explicitly

Run the approval cell only after reviewing the request above. To reject, replace the decision with `{"type": "reject", "message": "Reason"}`."""),
        code("""from langgraph.types import Command

if not requests:
    print("No mutation is waiting for approval.")
else:
    decisions = [{"type": "approve"} for _ in requests]
    result = asyncio.run(agent.ainvoke(
        Command(resume={"decisions": decisions}),
        config=run_config,
    ))
    result["messages"][-1].pretty_print()
"""),
        md("""## 10. Durable state across CLI sessions

Create a new thread with no prior conversation history and ask for the event. If the event appears, SQLite—not conversational memory—is carrying the family fact across sessions."""),
        md("![New session, same family calendar](./images/10_img.png)\n"),
        code("""verify_config = {
    "configurable": {"thread_id": f"notebook-verify-{uuid4()}"},
    "recursion_limit": 30,
}
verify_result = asyncio.run(agent.ainvoke(
    {"messages": [{"role": "user", "content": f"Show activities on {demo_day.isoformat()} for family-1"}]},
    config=verify_config,
))
verify_result["messages"][-1].pretty_print()
"""),
        md("""## 11. Family outing research with You.com

The Family Outing Agent checks calendar and school commitments through one
controlled `research_family_outings` wrapper. The hosted connection discovers
seven You.com tools, but the specialist receives only the wrapper, which uses
`you-search` and `you-contents`. The model explains cited results without
inventing hours, prices, tickets, travel time, or suitability. Search results
are proposals and never become calendar events without a separate approved
calendar action."""),
        code("""outing_prompt = (
    "Find three science or outdoor activities near San Jose for family-1 this "
    "weekend. Check our family and school calendars first, stay within a "
    "45-minute drive, preserve source URLs, and do not add anything to the calendar."
)
print("Try this after adding YDC_API_KEY to .env:\\n", outing_prompt)
"""),
        md("""## 12. Deep weekly coordination + school calendar

This is the workflow that makes the project visibly more agentic than a tool router. A weekly request requires several isolated specialists and shared artifacts:

1. **Intake Agent** normalizes the week and family goal.
2. **Weekly Planner** loads existing family events and Reed school events.
3. **Transportation Agent** calls the deterministic availability, transportation, and candidate tools to produce three ranked options.
4. **Schedule Reviewer** audits the recommended option—not one event at a time.
5. A rejected review loops back to planning for revision and another review.
6. **Reminder Agent** drafts reminders only after review approval.
7. Proposed writes carry expected versions and are emitted together so the parent sees one grouped approval set.

The school source is the supplied Reed Elementary 2026–2027 calendar. Its dates are subject to change, so this is reviewed project data rather than a live school feed."""),
        code("""import json

school_calendar = json.loads(
    Path("data/reed_elementary_2026_2027.json").read_text()
)
print(school_calendar["school"], school_calendar["school_year"])
print("Transcribed events:", len(school_calendar["events"]))

weekly_prompt = (
    "Coordinate next week for family-1, identify family, school, and transportation "
    "conflicts, generate three options for parent-1, parent-2, and vikram, recommend "
    "the best reviewed plan, and draft reminders without applying changes."
)
print("\\nTry this deep workflow in the CLI:\\n", weekly_prompt)
"""),
        md("""## 13. Seeded month and Kinday calendar

`tools/seed_month_demo.py` idempotently creates 21 realistic `family-1` events
from August 30 through September 29, 2026. The separate hosted Kinday frontend
shows a snapshot of those records in month, week, day, and list views. SQLite
remains authoritative; the hosted snapshot does not update automatically after
later CLI mutations."""),
        code("""seed_command = (
    "python tools/seed_month_demo.py --database data/family_activity.db "
    "--start 2026-08-29"
)
print("Seed the demo month with:\\n", seed_command)
print("Kinday: https://kinday-family-planner.anusha-akkiraj319688.chatgpt.site")
"""),
        md("""## Recap

You built a family activity system that demonstrates the course's core agentic requirements:

- A **Deep Agent coordinator** that routes and delegates.
- Eight **specialist subagents**, including outing research, transportation planning, and independent review.
- **Eighteen local MCP tools** plus seven discoverable hosted You.com tools; outing research is constrained behind a controlled wrapper.
- A **review/revision loop** with shared weekly-plan artifacts.
- **Human approval** before every write.
- **Deterministic Python safeguards** for past times, conflicts, versions, family scope, availability, transportation, candidate scoring, and idempotency.
- **Draft-only reminders** with no external messaging side effects.
- **SQLite persistence across fresh CLI sessions**, with no need for conversational memory.
- `recursion_limit` as the safety backstop.

**Where to take it next:** add live Kinday/SQLite synchronization, authenticated family membership, Google Calendar synchronization, and an optional Twilio worker after the draft-only MVP is accepted."""),
    ]

    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "family-activity-agent (.venv)",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.13",
                "mimetype": "text/x-python",
                "codemirror_mode": {"name": "ipython", "version": 3},
                "pygments_lexer": "ipython3",
                "nbconvert_exporter": "python",
                "file_extension": ".py",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    NOTEBOOK_PATH.write_text(json.dumps(notebook, indent=1) + "\n")


if __name__ == "__main__":
    build_docx()
    build_notebook()
    print(DOCX_PATH)
    print(NOTEBOOK_PATH)
