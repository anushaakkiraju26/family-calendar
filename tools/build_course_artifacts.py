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
    set_run_font(summary.add_run("Working CLI MVP with Deep Agents, LangGraph, Groq, MCP tools, SQLite persistence, human approval, deterministic validation, offline evaluations, and optional LangSmith tracing."))


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
        "My agent helps parents coordinate family activities in a CLI-backed shared calendar, replacing scattered messages and manual cross-checking. It autonomously resolves requests, reads calendar state, checks conflicts, and drafts reminders using 10 MCP tools; it hands off to a parent before every create, update, delete, restore, or reminder change, and succeeds when a parent can complete a calendar task in under two minutes with no unapproved writes."
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
        "A web or mobile frontend; the course MVP uses a CLI.",
        "Authentication, production tenant identity, and phone-number management.",
        "Calendar synchronization with Google Calendar or Apple Calendar.",
        "Recurring-event series editing and transportation optimization.",
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
    └── Reminder Agent ─── reminder drafts
              │
              ▼
      MCP Tool Server (stdio)
              │
       ┌──────┴────────┐
       ▼               ▼
CalendarRepository   10 typed tools
       │
       ▼
SQLite: events + reminders + audit_logs""")

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
        ["schedule_reminder", "Write", "Store one reminder draft.", "Required"],
        ["schedule_day_of_reminders", "Write", "Atomically store drafts for both parents.", "Required"],
        ["list_reminders", "Read", "Review reminder drafts and statuses.", "No"],
        ["cancel_reminders", "Write", "Cancel pending drafts for an event.", "Required"],
    ], [1.7, 0.65, 3.15, 1.0])

    doc.add_heading("9. Data and Persistence", level=1)
    doc.add_paragraph("No external dataset is required. The application uses synthetic course-demo family data stored in three SQLite tables.")
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
        ["Groq 429 / timeout", "CLI returns a concise retry message instead of a traceback."],
        ["MCP or SQLite failure", "No success is assumed; user is told to verify state before retrying."],
        ["Rejected approval", "Pending tool call is not executed."],
        ["Stale agent artifact", "Known temporary JSON files are cleared at the next CLI start."],
    ], [2.0, 4.5])

    doc.add_heading("13. Evaluation Strategy", level=1)
    doc.add_paragraph("The offline suite contains 22 passing tests and does not consume Groq quota. It verifies repository rules plus the actual Deep Agent, LangGraph interrupt/resume flow, MCP subprocess, and SQLite mutation boundary using a deterministic fake chat model.")
    add_bullets(doc, [
        "Real MCP read invocation through a managed stdio subprocess.",
        "Mutation absent before approval and present only after resume approval.",
        "Create/list/update/delete/restore lifecycle and family isolation.",
        "Past-event, conflict, reminder, version, and idempotency failure paths.",
        "CLI rate-limit, timeout, connection, database, and unknown-error formatting.",
        "Fourteen natural-language evaluation cases with expected tools and outcomes.",
    ])

    doc.add_heading("14. Configuration and Runbook", level=1)
    add_code_block(doc, """cd /Users/anushaakkiraju/family-activity-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
# Add GROQ_API_KEY. Optionally add LANGSMITH_API_KEY.
pytest
family-activity-agent 'Show activities today for family-1'""")
    doc.add_paragraph("Optional LangSmith tracing uses LANGSMITH_TRACING=true and project family-activity-agent-mvp. Course traces should use synthetic names and schedules because traces can contain prompts and tool results.")

    doc.add_heading("15. Representative Vibe-Coding Prompts and Iterations", level=1)
    add_bullets(doc, [
        "Create a standalone MCP server with event lifecycle and reminder tools; do not reuse the home-buying project.",
        "Build a Deep Agent coordinator with intake, calendar, conflict, and reminder specialists.",
        "Switch the model provider to Groq and reduce latency/tool-message incompatibilities.",
        "Use Pacific timezone and school hours from family preferences.",
        "Add soft deletion, restoration, both-parent reminder drafts, and approval gates.",
        "Prevent false success when the agent writes a plan but does not execute the MCP tool.",
        "Reject past events and enforce parent/child conflicts deterministically.",
        "Add offline end-to-end evaluations and optional LangSmith tracing.",
    ])
    doc.add_paragraph("Key learning: prompts guide behavior, but high-risk invariants belong in deterministic tools and repository transactions. Tool results—not model prose—must be the evidence for completion.")

    doc.add_heading("16. Demo Script (5 Minutes or Less)", level=1)
    add_numbered(doc, [
        "Show the architecture and identify the coordinator, four subagents, MCP server, and SQLite state.",
        "Create a future event and pause at the create_event approval prompt; approve it.",
        "List the event to prove persistence in a separate CLI command.",
        "Create a different child's overlapping event to show that it is allowed.",
        "Attempt to assign both overlapping events to one parent and show the conflict with no update.",
        "Draft a day-of reminder for both parents and emphasize that no SMS is sent.",
        "Delete and restore an event to demonstrate reversible writes.",
        "Show pytest output (22 passing) and one LangSmith trace tree using synthetic data.",
    ])

    doc.add_heading("17. Validation Checklist", level=1)
    add_table(doc, ["Before demo", "During / after demo"], [
        ["Virtual environment active", "Every write displays an approval prompt"],
        ["GROQ_API_KEY configured", "Past event is rejected"],
        ["Optional LangSmith key configured", "Parent conflict is detected"],
        ["pytest passes", "Reminder is described as a saved draft"],
        ["Synthetic demo data selected", "Separate CLI read proves SQLite persistence"],
        ["No secrets shown on screen", "Trace and test evidence captured"],
    ], [3.25, 3.25])

    doc.add_heading("18. Current Implementation Boundary and Extensions", level=1)
    add_code_block(doc, """UNDERSTAND REQUEST → READ CALENDAR → CHECK POLICY/CONFLICTS
→ HUMAN APPROVAL FOR WRITE → MCP MUTATION → SQLITE + AUDIT LOG
→ VERIFIED RESPONSE → STOP""")
    doc.add_paragraph("The MVP stops after saving calendar state or reminder drafts. It does not send messages or perform external commitments. Future extensions include Twilio delivery, authenticated family membership, a shared calendar frontend, Google/Apple Calendar synchronization, recurring events, production PostgreSQL, and hosted deployment.")

    doc.core_properties.title = "Family Activity Deep Agent — Week 3 Project Documentation"
    doc.core_properties.subject = "Agentic AI Systems course project"
    doc.core_properties.author = "Family Activity Agent Project"
    doc.save(DOCX_PATH)


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": text.splitlines(keepends=True)}


def build_notebook_diagrams():
    """Create GitHub/Jupyter-renderable architecture illustrations."""
    IMAGES.mkdir(parents=True, exist_ok=True)
    diagrams = {
        "01_architecture.svg": ("Family Activity Deep Agent — Architecture", ["Parent CLI", "Deep Agent\nCoordinator", "MCP Tool\nServer", "SQLite\nCalendar"], "Natural language → orchestration → typed tools → durable state"),
        "02_mcp_tools.svg": ("MCP Tool Boundary", ["Read tools\nlist + conflicts", "Write tools\nevent lifecycle", "HITL gate\napproval", "Repository\nvalidation"], "Reads are autonomous; every write pauses before execution"),
        "03_skills.svg": ("Skills — Progressive Disclosure", ["Skill catalog\ndescriptions", "Relevant\nSKILL.md", "Coordinator or\nspecialist", "Policy-aware\ntool call"], "Calendar policy • Reminder policy • Family preferences"),
        "04_state.svg": ("State and Memory Boundary", ["CLI request\nnew thread", "In-memory\napproval state", "Temporary\nJSON artifacts", "SQLite\ndurable truth"], "Conversation is ephemeral; events, reminders, and audits persist"),
        "05_subagents.svg": ("Coordinator and Specialist Agents", ["Intake\nnormalize", "Calendar\nevent lifecycle", "Conflict\nexplain overlaps", "Reminder\ndraft messages"], "The coordinator delegates only when specialization adds value"),
        "06_hitl.svg": ("Human-in-the-Loop Write Gate", ["Proposed\nmutation", "Pending\napproval", "Approve or\nreject", "Execute and\nverify"], "No approval → no database mutation"),
        "07_conflicts.svg": ("Deterministic Conflict Safety", ["Proposed\nevent", "Compare child\nand parent", "Repository\ntransaction", "Allow or\nreject"], "Critical overlap rules are enforced in code, not only prompts"),
        "08_evaluations.svg": ("Offline End-to-End Evaluations", ["Fake tool-calling\nmodel", "Deep Agent +\nLangGraph", "Real MCP\nsubprocess", "Temporary\nSQLite"], "Repeatable verification without consuming Groq quota"),
        "09_langsmith.svg": ("LangSmith Trace Tree", ["Root request\ntrace", "Coordinator\nmodel calls", "MCP tool\nspans", "Result and\nlatency"], "Synthetic demo data only—traces can contain prompts and tool results"),
    }
    fills = ["E8F0FE", "E6F4EA", "FEF7E0", "FCE8E6"]
    strokes = ["1A73E8", "188038", "F9AB00", "D93025"]
    for filename, (title, boxes, footer) in diagrams.items():
        box_w, box_h, gap, start_x, y = 205, 120, 45, 65, 135
        parts = [
            '<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="420" viewBox="0 0 1100 420">',
            '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#5F6368"/></marker></defs>',
            '<rect width="1100" height="420" rx="24" fill="#FFFFFF" stroke="#DADCE0"/>',
            f'<text x="550" y="55" text-anchor="middle" font-family="Arial, sans-serif" font-size="28" font-weight="600" fill="#202124">{title}</text>',
        ]
        for index, label in enumerate(boxes):
            x = start_x + index * (box_w + gap)
            parts.append(f'<rect x="{x}" y="{y}" width="{box_w}" height="{box_h}" rx="16" fill="#{fills[index]}" stroke="#{strokes[index]}" stroke-width="2"/>')
            lines = label.split("\n")
            base_y = y + 53 - (len(lines) - 1) * 14
            for line_index, line in enumerate(lines):
                parts.append(f'<text x="{x + box_w / 2}" y="{base_y + line_index * 30}" text-anchor="middle" font-family="Arial, sans-serif" font-size="19" font-weight="600" fill="#202124">{line}</text>')
            if index < len(boxes) - 1:
                x1, x2, arrow_y = x + box_w + 8, x + box_w + gap - 8, y + box_h / 2
                parts.append(f'<line x1="{x1}" y1="{arrow_y}" x2="{x2}" y2="{arrow_y}" stroke="#5F6368" stroke-width="3" marker-end="url(#arrow)"/>')
        parts.extend([
            f'<text x="550" y="325" text-anchor="middle" font-family="Arial, sans-serif" font-size="19" fill="#5F6368">{footer}</text>',
            '<text x="550" y="372" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" fill="#80868B">Family Activity Agent • Course MVP</text>',
            "</svg>",
        ])
        (IMAGES / filename).write_text("\n".join(parts))


def build_notebook():
    build_notebook_diagrams()
    cells = [
        md("""# Family Activity Deep Agent — Shared Calendar & Reminder Drafts

A hands-on tutorial of the **Deep Agents** framework with a standalone **MCP tool server** and durable **SQLite** calendar state.

We build a family coordinator that creates, reads, updates, deletes, and restores activities; detects child and parent conflicts; and stores reviewable reminder drafts.

> **Draft-only messaging.** The MVP stores reminder text but does not send SMS messages. Every calendar or reminder mutation pauses for parent approval."""),
        md("""## Architecture at a glance

```
Parent request → Family Coordinator (plans, routes, verifies)
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       Intake         Calendar       Conflict        Reminder
       Agent           Agent          Agent           Agent
          └──────────────┴──────┬───────┴──────────────┘
                                ▼
                      Family Activity MCP Server
                                ▼
                  SQLite: events | reminders | audit_logs
```

| Deep Agents concept | Implementation |
|---|---|
| Planning and routing | Coordinator fast path plus specialist delegation |
| Subagents | Intake, calendar, conflict, and reminder specialists |
| Shared temporary state | `/work`, `/reviews`, and `/final` JSON artifacts |
| Skills | Calendar policy, reminder policy, and family preferences |
| Durable state | SQLite only; each CLI/notebook request is independent |
| Human-in-the-loop | LangGraph interrupts on all write tools |
| Deterministic safety | Repository validates future times, versions, and overlaps |
| Observability | Optional LangSmith trace tree |
"""),
        md("![Family Activity Deep Agent architecture](./images/01_architecture.svg)\n"),
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
if not os.getenv("GROQ_API_KEY"):
    raise RuntimeError("Add GROQ_API_KEY to .env before running the live agent cells.")

if os.getenv("LANGSMITH_API_KEY", "").strip():
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ.setdefault("LANGSMITH_PROJECT", "family-activity-agent-mvp")
    print("LangSmith tracing: ENABLED")
else:
    os.environ["LANGSMITH_TRACING"] = "false"
    print("LangSmith tracing: disabled")

print("Model:", os.getenv("FAMILY_ACTIVITY_MODEL", "openai/gpt-oss-20b"))
"""),
        md("""## 2. MCP tools

The Deep Agent launches the local MCP server as a managed stdio subprocess. Tool definitions live in `src/family_activity_mcp/server.py`; validation and SQLite transactions live in `repository.py`."""),
        md("![MCP tool boundary](./images/02_mcp_tools.svg)\n"),
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
        md("""## 3. Skills (progressive disclosure)

The coordinator sees skill descriptions first and loads full `SKILL.md` instructions only when relevant. This keeps the always-on prompt smaller while preserving domain policy."""),
        md("![Skills progressive disclosure](./images/03_skills.svg)\n"),
        code("""for path in sorted(Path("skills").glob("*/SKILL.md")):
    print(f"\\n===== {path} =====")
    print(path.read_text())
"""),
        md("""## 4. State boundary

SQLite is the sole durable source of truth. The checkpointer is in-memory because it is needed only to pause and resume approval within the current process. Temporary planning artifacts are cleared at the start of each request so stale files cannot influence a new command."""),
        md("![State and memory boundary](./images/04_state.svg)\n"),
        code("""from family_activity_agent.cli import RUN_ARTIFACTS

print("Durable state: data/family_activity.db")
print("Ephemeral per-run artifacts:")
for artifact in RUN_ARTIFACTS:
    print(" -", artifact)
"""),
        md("""## 5. Specialist subagents

Each specialist has a focused prompt and restricted tool set. The coordinator handles simple requests directly to reduce latency and delegates only when specialization adds value."""),
        md("![Coordinator and specialist agents](./images/05_subagents.svg)\n"),
        code("""from family_activity_agent.prompts import (
    INTAKE_PROMPT, CALENDAR_PROMPT, CONFLICT_PROMPT, REMINDER_PROMPT
)

subagents = {
    "intake-agent": "Normalizes ambiguous or multi-activity requests",
    "calendar-agent": "Handles complex event lifecycle operations",
    "conflict-agent": "Explains overlaps without mutating state",
    "reminder-agent": "Creates and manages reminder drafts",
}
for name, purpose in subagents.items():
    print(f"{name}: {purpose}")
"""),
        md("""## 6. Assemble the Deep Agent

`build_family_agent()` discovers MCP tools, wraps their results for Groq compatibility, registers subagents and skills, and configures interrupts on every mutating tool."""),
        code("""from family_activity_agent.agent import build_family_agent

agent = asyncio.run(build_family_agent())
print("Deep Agent assembled:", agent.name)
"""),
        md("""## 7. Run a read-only request

Read tools do not require approval. Use synthetic demo data when LangSmith tracing is enabled."""),
        code("""read_config = {
    "configurable": {"thread_id": f"notebook-read-{uuid4()}"},
    "recursion_limit": 30,
    "run_name": "family-activity-notebook-read",
    "tags": ["family-activity-agent", "notebook", "demo"],
}

read_result = asyncio.run(agent.ainvoke(
    {"messages": [{"role": "user", "content": "Show today's activities for family-1"}]},
    config=read_config,
))
read_result["messages"][-1].pretty_print()
"""),
        md("""## 8. Human-in-the-loop event creation

The next cell proposes a future event. The graph must stop before `create_event`; inspect the exact tool arguments before approving."""),
        md("![Human-in-the-loop write gate](./images/06_hitl.svg)\n"),
        code("""from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

demo_day = (datetime.now(ZoneInfo("America/Los_Angeles")) + timedelta(days=7)).date()
write_config = {
    "configurable": {"thread_id": f"notebook-write-{uuid4()}"},
    "recursion_limit": 30,
    "run_name": "family-activity-notebook-write",
    "tags": ["family-activity-agent", "notebook", "demo"],
}
prompt = (
    f"Add Demo Child's soccer practice on {demo_day.isoformat()} "
    "from 4 to 5 PM for family-1"
)
write_result = asyncio.run(agent.ainvoke(
    {"messages": [{"role": "user", "content": prompt}]},
    config=write_config,
))
print("Paused for approval:", "__interrupt__" in write_result)
"""),
        code("""from family_activity_agent.cli import pending_requests

requests = pending_requests(write_result)
for request in requests:
    print("PENDING APPROVAL:", request)
"""),
        md("""### Approve or reject explicitly

Run the approval cell only after reviewing the request above. To reject, replace the decision with `{"type": "reject", "message": "Reason"}`."""),
        code("""from langgraph.types import Command

if not requests:
    print("No mutation is waiting for approval.")
else:
    decisions = [{"type": "approve"} for _ in requests]
    write_result = asyncio.run(agent.ainvoke(
        Command(resume={"decisions": decisions}),
        config=write_config,
    ))
    write_result["messages"][-1].pretty_print()
"""),
        md("""## 9. Verify durable state

Use a separate read request. The new thread has no conversation history, so seeing the event proves that SQLite—not memory—is carrying the state."""),
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
        md("""## 10. Conflict safety

Different children may have overlapping activities. Assigning overlapping events to the same parent is rejected deterministically by the repository, even if the model skips an explanatory check."""),
        md("![Deterministic conflict safety](./images/07_conflicts.svg)\n"),
        code("""print(
    "Try in the CLI:",
    'family-activity-agent "Assign two overlapping activities in family-1 to parent-1"',
    sep="\\n",
)
"""),
        md("""## 11. Reminder drafts

The reminder tool stores recipient IDs, scheduled time, channel, and `message_body`. It does **not** call Twilio and the agent must never promise delivery."""),
        code("""print(
    "Example request:",
    "Draft a day-of reminder at 8 AM Pacific for both parents "
    "for Demo Child's next soccer practice in family-1",
    sep="\\n",
)
"""),
        md("""## 12. Offline evaluations

The automated suite uses a deterministic fake chat model but retains the actual Deep Agent, LangGraph interrupts, MCP subprocess, and SQLite layers. This avoids Groq quota use in CI."""),
        md("![Offline end-to-end evaluations](./images/08_evaluations.svg)\n"),
        code("""# Run from a notebook cell if desired:
# !pytest -q

import json
cases = json.loads(Path("evaluations/cases.json").read_text())
print(f"Evaluation cases: {len(cases)}")
for case in cases[:5]:
    print(f"- {case['id']}: {case['expected_outcome']}")
"""),
        md("""## 13. LangSmith observability

When enabled, the trace shows the coordinator at the root, model calls and MCP tools as nested spans, and approval/resumption across the workflow. Use only synthetic family data in traced demonstrations."""),
        md("![LangSmith trace tree](./images/09_langsmith.svg)\n"),
        code("""print("LangSmith project:", os.getenv("LANGSMITH_PROJECT", "not configured"))
print("Tracing enabled:", os.getenv("LANGSMITH_TRACING", "false"))
"""),
        md("""## Recap

You built a family activity system that demonstrates the course's core agentic requirements:

- A **Deep Agent coordinator** that routes and delegates.
- Four **specialist subagents** with focused prompts and tools.
- Ten typed **MCP tools** backed by SQLite.
- **Human approval** before every write.
- **Deterministic safety** for past times, conflicts, versions, and idempotency.
- **Draft-only reminders** with no external messaging side effects.
- A deliberate **state boundary**: durable database, ephemeral conversation.
- **Offline evaluations** and optional **LangSmith tracing**.

**Where to take it next:** add a shared calendar frontend, authenticated family membership, Google Calendar synchronization, and an optional Twilio worker after the draft-only MVP is accepted."""),
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
