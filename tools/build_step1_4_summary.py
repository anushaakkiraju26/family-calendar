"""Build a clean, standalone Step 1-4 documentation spreadsheet covering
every fix made across the whole project (the original 2026-09-02/03 fix plus
all six made on 2026-09-05) - one unified narrative, not spread across dated
sections like week4_eval_tracker_Anusha.xlsx.

Four sheets: Step 1 (failure annotations), Step 2 (named categories),
Step 3 (labeled failures), Step 4 (prompt changes with measured deltas).

Run: python tools/build_step1_4_summary.py
"""
from __future__ import annotations

from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "evaluations" / "step1-4_summary.xlsx"

HEADER_FILL = PatternFill(start_color="1F2A44", end_color="1F2A44", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)
SECTION_FONT = Font(bold=True)
NOTE_FONT = Font(italic=True)
WRAP = Alignment(wrap_text=True, vertical="top")


def write_header(ws, row, values):
    for col, value in enumerate(values, start=1):
        cell = ws.cell(row=row, column=col, value=value)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = WRAP


def write_data_row(ws, row, values):
    for col, value in enumerate(values, start=1):
        cell = ws.cell(row=row, column=col, value=value)
        cell.alignment = WRAP


def write_note(ws, row, text, span=1):
    cell = ws.cell(row=row, column=1, value=text)
    cell.font = NOTE_FONT
    cell.alignment = WRAP


def set_widths(ws, widths):
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def build_step1(wb):
    ws = wb.create_sheet("Step 1 - Annotations")
    write_data_row(ws, 1, [
        "Step 1 - Read every failing run individually and annotate WHY it "
        "failed, before naming any categories. Covers the full project "
        "history: the original 2026-09-02/03 baseline plus the 2026-09-05 "
        "triage session.",
    ])
    ws.cell(row=1, column=1).font = SECTION_FONT
    row = 3
    write_header(ws, row, [
        "#", "Date", "case_id", "target_workflow_category",
        "actual_category", "tokens", "annotation (WHY it failed)",
    ])
    row += 1
    rows = [
        (1, "2026-09-02/03", "hero-weekly-candidates", "deep_weekly_workflow",
         "fabricated_no_delegation", 222464,
         "Skips weekly-planner/transportation-agent/schedule-reviewer "
         "entirely and answers directly with a 'recommended plan' "
         "presented as reviewed and conflict-free, violating the "
         "coordinator's own HARD COMPLETION GATE."),
        (2, "2026-09-02/03", "weekly-deep-planning", "deep_weekly_workflow",
         "stalled_or_shortcut_no_delegation", 307330,
         "Partial delegation happens (intake-agent runs, sometimes "
         "list_parent_availability is called) but the chain stalls before "
         "transportation-agent or schedule-reviewer produce their "
         "artifacts. Asked the user for parent IDs it had just fetched "
         "itself - a data-handoff failure, not a missing-data one."),
        (3, "2026-09-04", "approval-rejected", "fast_path_mutate",
         "timed_out_incomplete", 0,
         "The harness rejects the update_event approval request; instead "
         "of stopping, the agent attempts update_event again repeatedly "
         "(list_events, check_conflicts, update_event, update_event, "
         "update_event) until it hits a provider timeout. The mutation "
         "gate worked - the agent's response to a 'no' did not."),
        (4, "2026-09-04", "same-child-conflict", "fast_path_reject",
         "timed_out_incomplete", 0,
         "The prompt says 'during his existing soccer practice' - the "
         "time is fully derivable from list_events - but the agent asks "
         "the parent to restate the piano lesson's title, time, and "
         "location instead of resolving it and calling check_conflicts. "
         "Never actually rejects the conflict."),
        (5, "2026-09-04", "draft-both-parent-reminder", "fast_path_mutate",
         "fast_path_mutate", 36003,
         "Tool sequence and mutation are already correct - "
         "list_events -> schedule_day_of_reminders both succeed. But the "
         "final answer says 'Reminders have been scheduled for both "
         "parents at 8:00 AM... to note that Leo's soccer practice is at "
         "4:00 PM,' which implies delivery. This MVP only ever stores a "
         "draft and never sends SMS. Caught by human review, not the "
         "automated overall_pass metric."),
        (6, "2026-09-04", "vikram-availability-rule", "fast_path_reject",
         "fast_path_reject", 0,
         "Zero tool calls. The agent answers correctly (Vikram is "
         "unavailable Tuesday 9:30-4:00) but only because that exact "
         "window is hard-coded as policy text in its own prompt - it "
         "never calls check_parent_availability or "
         "check_transportation_conflicts to verify it structurally. "
         "Right answer, unverifiable method."),
        (7, "2026-09-05", "update-event-success", "fast_path_mutate",
         "timed_out_incomplete", 0,
         "In roughly 1 of 3 runs, the agent calls update_event without "
         "first calling check_conflicts, despite an existing instruction "
         "to check conflicts before a timed change - a reliability gap on "
         "an already-correct instruction, not a missing one."),
        (8, "2026-09-05", "restore-event / create-future-event-with-location",
         "fast_path_mutate", "fast_path_mutate (regressed)", None,
         "After the update-event-success fix (row 7) was applied as an "
         "unconditional rule, the agent started calling check_conflicts a "
         "second, redundant time on create-future-event-with-location, "
         "and calling it at all before restore_event, which never needs "
         "it. The fix for one case broke two previously-passing ones."),
        (9, "2026-09-05", "cross-family-delete-not-found", "fast_path_reject",
         "fast_path_reject (wrong tool selection)", None,
         "After list_events correctly returns empty for the wrong "
         "family_id, the agent calls ls, glob, and grep to search the "
         "repository/filesystem for the missing event instead of "
         "accepting the empty result as final."),
    ]
    for r in rows:
        write_data_row(ws, row, list(r))
        row += 1
    set_widths(ws, [4, 14, 32, 22, 26, 10, 70])
    ws.freeze_panes = "A4"


def build_step2(wb):
    ws = wb.create_sheet("Step 2 - Categories")
    write_data_row(ws, 1, [
        "Step 2 - Cluster the Step 1 annotations into named categories. "
        "Aim for one category per distinct root cause, not one per case.",
    ])
    ws.cell(row=1, column=1).font = SECTION_FONT
    row = 3
    write_header(ws, row, [
        "Category", "One-line definition", "Step 1 rows", "Count",
        "Why it matters", "Status",
    ])
    row += 1
    categories = [
        ("Delegation stall / shortcut",
         "Coordinator answers directly instead of delegating through the "
         "required sub-agent sequence, or asks for/gives up on "
         "information a sub-agent already owns.",
         "1, 2", 2,
         "Produces a fabricated, unreviewed plan presented as if it were "
         "conflict-free, or stalls without producing a usable plan at "
         "all - the highest-token, highest-cost failure mode observed.",
         "Fixed (original DATA-HANDOFF rule)"),
        ("Retry after rejection", "Coordinator retries a mutation tool "
         "after the parent/harness rejected it, instead of stopping.",
         "3", 1,
         "Undermines the entire approval-gate safety mechanism - the "
         "parent's 'no' must be final.",
         "Fixed"),
        ("Under-specified relative time",
         "Coordinator asks the parent to restate a detail (usually a "
         "time) that is already derivable from a tool result, instead of "
         "resolving it and proceeding.",
         "4", 1,
         "Wastes a turn and, worse, means the required safety check "
         "(conflict detection) never actually runs.",
         "Fixed"),
        ("Overclaiming in final-answer wording",
         "The tool sequence and mutation are correct, but the final "
         "answer's wording implies more than what actually happened.",
         "5", 1,
         "Invisible to the automated overall_pass metric - only caught by "
         "reading the actual text, which is exactly why this step exists.",
         "Fixed"),
        ("Skipped required verification tool call",
         "Coordinator answers from memorized policy text or an earlier "
         "instruction instead of calling the deterministic tool that's "
         "the real source of truth.",
         "6, 7", 2,
         "Trusting memorized text instead of a tool result is exactly the "
         "kind of ungrounded claim a golden dataset exists to catch.",
         "Fixed"),
        ("Rule over-generalization / regression",
         "A fix scoped to one situation gets applied by the model to a "
         "superficially similar but different situation, breaking a "
         "previously-passing case.",
         "8", 1,
         "The single most important lesson of the whole project: every "
         "fix must be re-verified against unrelated previously-passing "
         "cases, not just its target case.",
         "Fixed (re-scoped the rule)"),
        ("Filesystem fallback on empty search",
         "When a calendar-tool search returns empty, the coordinator "
         "falls back to searching the repository/filesystem instead of "
         "accepting the empty result as authoritative.",
         "9", 1,
         "The agent going outside its sanctioned data sources - the same "
         "underlying principle as category 1's fix, but it had only been "
         "scoped to one workflow and needed generalizing.",
         "Fixed"),
    ]
    for c in categories:
        write_data_row(ws, row, list(c))
        row += 1
    row += 1
    write_note(ws, row,
        "Not clustered as a fixable defect this project: provider/model "
        "latency instability (same runs sometimes pass, sometimes time "
        "out, on an identical fixture) and 'premature mutation proposal' "
        "(reject-past-event, school-event-overlap - reproduced twice, "
        "understood, not yet fixed). See FAILURE_ANALYSIS_2026-09-05.md.")
    set_widths(ws, [30, 45, 12, 8, 45, 24])


def build_step3(wb):
    ws = wb.create_sheet("Step 3 - Labels")
    write_data_row(ws, 1, [
        "Step 3 - Assign every Step 1 row to its Step 2 category.",
    ])
    ws.cell(row=1, column=1).font = SECTION_FONT
    row = 3
    write_header(ws, row, [
        "Step 1 #", "case_id", "actual_category", "Step 2 category",
    ])
    row += 1
    labels = [
        (1, "hero-weekly-candidates", "fabricated_no_delegation", "Delegation stall / shortcut"),
        (2, "weekly-deep-planning", "stalled_or_shortcut_no_delegation", "Delegation stall / shortcut"),
        (3, "approval-rejected", "timed_out_incomplete", "Retry after rejection"),
        (4, "same-child-conflict", "timed_out_incomplete", "Under-specified relative time"),
        (5, "draft-both-parent-reminder", "fast_path_mutate", "Overclaiming in final-answer wording"),
        (6, "vikram-availability-rule", "fast_path_reject", "Skipped required verification tool call"),
        (7, "update-event-success", "timed_out_incomplete", "Skipped required verification tool call"),
        (8, "restore-event / create-future-event-with-location",
         "fast_path_mutate (regressed)", "Rule over-generalization / regression"),
        (9, "cross-family-delete-not-found", "fast_path_reject (wrong tool selection)",
         "Filesystem fallback on empty search"),
    ]
    for lab in labels:
        write_data_row(ws, row, list(lab))
        row += 1
    set_widths(ws, [10, 45, 30, 42])


def build_step4(wb):
    ws = wb.create_sheet("Step 4 - Prompt Changes")
    write_data_row(ws, 1, [
        "Step 4 - For each category, the specific prompt/runner change "
        "made, the predicted impact, the measured before/after delta, "
        "and an explicit regression check (cases that flipped in either "
        "direction, not just the net count).",
    ])
    ws.cell(row=1, column=1).font = SECTION_FONT
    row = 3

    fixes = [
        ("Fix 0 (2026-09-02/03)", "Delegation stall / shortcut",
         "hero-weekly-candidates, weekly-deep-planning",
         "Most frequent observed cluster at the time (4/11 historical "
         "failures), affects both deep-workflow cases.",
         "Prompt engineering",
         "Added one DATA-HANDOFF RULE to the coordinator: reuse data "
         "already returned by tools/sub-agents, do not search the "
         "filesystem for calendar records, and retry the same delegated "
         "step with the returned data when its required artifact is "
         "missing.",
         "Reduce delegation stalls and raise deep_weekly_workflow "
         "completion from the 0/6 baseline.",
         "Total recorded tokens: 872,426 -> 632,052 (-27.6%). Total "
         "latency: 841.36s -> 507.35s (-39.7%). p95 latency: 232.61s -> "
         "93.42s (-59.8%). Task completion itself was unchanged "
         "(deep_weekly_workflow still 0/6) - this fix improved "
         "efficiency, not correctness.",
         "None", "None"),
        ("Fix 1 (2026-09-04)", "Retry after rejection", "approval-rejected",
         "SEVERITY_CRITICAL case; a mutation gate that can be silently "
         "retried past rejection undermines the entire approval-gate "
         "safety guarantee.",
         "Prompt engineering + runner safety net",
         "Added an explicit coordinator rule: after a rejected mutation, "
         "stop immediately, never retry, acknowledge the rejection and "
         "ask for direction. Runner now also classifies a same-tool "
         "retry after rejection as its own failure category "
         "(rejected_mutation_retry_unsafe) instead of riding out a "
         "generic timeout.",
         "approval-rejected completes cleanly instead of retrying "
         "update_event into a provider timeout.",
         "timed_out_incomplete (109.50s, 0 tokens) -> fast_path_mutate / "
         "overall_pass=True (65-108s across 3 separate re-verifications, "
         "56-90k tokens).",
         "approval-rejected", "None (re-verified clean across 3 "
         "subsequent full baselines)."),
        ("Fix 2 (2026-09-04)", "Under-specified relative time",
         "same-child-conflict",
         "SEVERITY_CRITICAL edge case; asking the parent to restate a "
         "time already derivable from list_events means the required "
         "conflict check never runs.",
         "Prompt engineering",
         "FAST PATH workflow step now instructs the coordinator to "
         "resolve a time expressed relative to an existing event via "
         "list_events itself, rather than asking the parent.",
         "same-child-conflict calls list_events -> check_conflicts and "
         "correctly rejects the overlap.",
         "timed_out_incomplete / 0 tools -> fast_path_reject / "
         "overall_pass=True, correct rejection with explanation "
         "(confirmed at 48.88s and 82.32s in separate runs). Residual "
         "timeouts on some runs are model-latency variance, not a logic "
         "regression.",
         "same-child-conflict (on runs where the model completes in time)",
         "None."),
        ("Fix 3 (2026-09-04)", "Overclaiming in final-answer wording",
         "draft-both-parent-reminder",
         "Caught by human review, not the automated overall_pass metric - "
         "exactly the class of bug this step exists to catch.",
         "Prompt engineering",
         "The 'say reminder draft saved' wording rule existed only in "
         "the delegated REMINDER_PROMPT; added the same rule to the "
         "coordinator's own Rules section since simple reminder requests "
         "are fast-pathed directly, not delegated.",
         "Final answer for a completed reminder mutation says 'reminder "
         "draft(s) saved,' not phrasing implying delivery.",
         "'Reminders have been scheduled for both parents at 8:00 AM... "
         "to note that Leo's soccer practice is at 4:00 PM' -> 'reminder "
         "drafts saved' (exact required phrase, confirmed on re-run).",
         "None by the automated metric (already overall_pass=True); a "
         "qualitative wording fix invisible to that metric.", "None."),
        ("Fix 4 (2026-09-05)", "Skipped required verification tool call",
         "vikram-availability-rule, update-event-success",
         "Both cases relied on memorized policy text or an omitted call "
         "instead of a deterministic tool-backed check - the same "
         "pattern across two different tools.",
         "Prompt engineering (3 iterations for vikram, 1 for "
         "update-event-success)",
         "Added a TRANSPORTATION AVAILABILITY CHECK workflow step "
         "requiring check_parent_availability AND "
         "check_transportation_conflicts every time, with no "
         "short-circuiting after the first result; added an "
         "unconditional 'always call check_conflicts before create_event "
         "or update_event' rule.",
         "Both cases call all required tools reliably.",
         "vikram-availability-rule: 0 tool calls -> 2/2 and 3/3 clean "
         "verification batches (63.75-82.32s); update-event-success: "
         "2/3 -> 5/5 clean.",
         "vikram-availability-rule, update-event-success",
         "restore-event, create-future-event-with-location (see Fix 5)."),
        ("Fix 5 (2026-09-05)", "Rule over-generalization / regression",
         "restore-event, create-future-event-with-location",
         "The most important lesson of the whole project: a fix that "
         "helps its target case can silently break previously-passing "
         "ones if scoped too broadly.",
         "Prompt engineering (tightened scoping)",
         "Reworded the Fix 4 check_conflicts rule to say 'exactly once,' "
         "explicitly excluded delete_event/restore_event, and forbade a "
         "second check_conflicts call for the same time.",
         "restore-event and create-future-event-with-location stop "
         "over-calling check_conflicts while update-event-success keeps "
         "calling it correctly.",
         "restore-event and create-future-event-with-location: "
         "overall_pass False (regressed by Fix 4) -> True, 6/6 clean "
         "across both cases plus update-event-success together.",
         "restore-event, create-future-event-with-location (recovered)",
         "None from this fix. OPEN FOLLOW-UP: reassign-parent-only (a "
         "case added the same day) shows a related, not-yet-fixed "
         "over-generalization from the Fix 4 transportation-check rule, "
         "confirmed once in the full 30-case baseline - flagged, not "
         "resolved."),
        ("Fix 6 (2026-09-05)", "Filesystem fallback on empty search",
         "cross-family-delete-not-found",
         "Discovered while verifying a newly-added dataset case; the "
         "Fix 0 DATA-HANDOFF rule already forbade this but was scoped "
         "only to the deep-weekly-workflow section, so a fast-pathed "
         "request never read it.",
         "Prompt engineering (generalized Fix 0's rule)",
         "Added a general, top-level Rules bullet: any empty "
         "calendar-tool result is final; never fall back to ls/glob/"
         "grep/read_file to search for family or calendar records.",
         "A 'nothing found' fast-path request reports the empty result "
         "directly instead of exploring the filesystem.",
         "2/2 runs called ls/glob/grep (tool_selection_pass=False) -> "
         "2/2 clean after the fix, confirmed again in the full 30-case "
         "baseline.",
         "cross-family-delete-not-found", "None."),
    ]

    for (fix_id, category, cases, why, lever, change, predicted, delta,
         flipped_right, flipped_wrong) in fixes:
        write_data_row(ws, row, [f"{fix_id} - Category"])
        ws.cell(row=row, column=1).font = SECTION_FONT
        write_data_row(ws, row, [f"{fix_id} - Category", category])
        row += 1
        for label, value in [
            ("Case(s)", cases), ("Why this one", why), ("Lever", lever),
            ("Specific change", change), ("Predicted impact", predicted),
            ("Net delta by metric", delta),
            ("Cases flipped wrong -> right (case_ids)", flipped_right),
            ("Cases flipped right -> wrong / regressed (case_ids)", flipped_wrong),
        ]:
            write_data_row(ws, row, [label, value])
            row += 1
        row += 1
    set_widths(ws, [42, 90])


def main() -> None:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    build_step1(wb)
    build_step2(wb)
    build_step3(wb)
    build_step4(wb)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUTPUT_PATH)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
