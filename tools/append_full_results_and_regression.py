"""Append two sheets to evaluations/step1-4_summary.xlsx:

1. "Full Results" - the actual "Completed Spreadsheet" checklist item: every
   case, one row per run, with ground truth label, model-predicted label,
   PASS/FAIL, and the participant-assigned failure category for every
   non-passing row (built from results_baseline.csv + cases.json).
2. "Regression Tests" - for each of the 7 fixes, the specific re-run of its
   target case(s) after the fix plus at least one previously-passing case
   re-verified, with an explicit regression-found column - not just prose.

Run: python tools/append_full_results_and_regression.py
"""
from __future__ import annotations

import json
from pathlib import Path

import openpyxl
import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_PATH = PROJECT_ROOT / "evaluations" / "step1-4_summary.xlsx"
CASES_PATH = PROJECT_ROOT / "evaluations" / "cases.json"
RESULTS_PATH = PROJECT_ROOT / "evaluations" / "results_baseline.csv"

HEADER_FILL = PatternFill(start_color="1F2A44", end_color="1F2A44", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)
SECTION_FONT = Font(bold=True)
WRAP = Alignment(wrap_text=True, vertical="top")

# Maps case_id -> failure category (from Step 2) for every non-passing row.
# "PASS" rows don't need a category. pending_fixture rows are marked as such.
FAILURE_CATEGORY = {
    "reject-past-event": "Premature mutation proposal (not yet fixed)",
    "same-child-conflict": "Provider/model latency instability",
    "same-parent-conflict": "Not yet triaged",
    "weekly-deep-planning": "Delegation stall / shortcut (deep-workflow non-termination, unresolved)",
    "school-event-overlap": "Premature mutation proposal (not yet fixed)",
    "hero-weekly-candidates": "Delegation stall / shortcut (deep-workflow non-termination, unresolved)",
    "vikram-availability-rule": "Provider/model latency instability",
    "stale-weekly-option": "Not yet triaged",
    "family-outing-weekend": "Not yet triaged (partial completion - artifact-write timing)",
    "reassign-parent-only": "Rule over-generalization / regression (open follow-up)",
}


def write_header(ws, row, values):
    for col, value in enumerate(values, start=1):
        cell = ws.cell(row=row, column=col, value=value)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = WRAP


def write_row(ws, row, values):
    for col, value in enumerate(values, start=1):
        cell = ws.cell(row=row, column=col, value=value)
        cell.alignment = WRAP


def set_widths(ws, widths):
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def build_full_results(wb):
    cases = {c["id"]: c for c in json.loads(CASES_PATH.read_text())}
    df = pd.read_csv(RESULTS_PATH)

    ws = wb.create_sheet("Full Results")
    write_row(ws, 1, [
        "Completed Spreadsheet - every case/run in the 30-case dataset: "
        "reviewed ground truth label, the model's predicted label, the "
        "PASS/FAIL comparison, and the participant-assigned failure "
        "category for every non-passing row. Source: cases.json (ground "
        "truth) joined with results_baseline.csv, the 2026-09-05 full "
        "30-case baseline (the model-predicted labels).",
    ])
    ws.cell(row=1, column=1).font = SECTION_FONT
    row = 3
    write_header(ws, row, [
        "case_id", "run", "ground_truth_label (target_workflow_category)",
        "model_predicted_label (actual_category)", "PASS/FAIL",
        "failure_category (participant-assigned)",
    ])
    row += 1

    for _, r in df.iterrows():
        case_id = r["case_id"]
        run_idx = r["run_index"]
        run_label = "" if pd.isna(run_idx) else int(run_idx)
        gt = r["target_workflow_category"]
        pred = r["actual_category"]
        if pred == "pending_fixture":
            verdict = "N/A"
            category = "N/A - fixture not yet implemented"
        else:
            verdict = "PASS" if bool(r["overall_pass"]) else "FAIL"
            category = "PASS" if verdict == "PASS" else FAILURE_CATEGORY.get(
                case_id, "Not yet triaged"
            )
        write_row(ws, row, [case_id, run_label, gt, pred, verdict, category])
        row += 1

    set_widths(ws, [34, 6, 30, 30, 10, 55])
    ws.freeze_panes = "A4"

    # Summary line
    row += 1
    live = df[df["actual_category"] != "pending_fixture"]
    write_row(ws, row, [
        f"Live: {live['overall_pass'].sum()}/{len(live)} strict pass "
        f"({live['overall_pass'].mean():.0%}). Routing-only pass: "
        f"{live['correct'].sum()}/{len(live)} ({live['correct'].mean():.0%}). "
        f"{len(df) - len(live)} rows still pending_fixture.",
    ])
    ws.cell(row=row, column=1).font = SECTION_FONT


def build_regression_tests(wb):
    ws = wb.create_sheet("Regression Tests")
    write_row(ws, 1, [
        "Regression Tests - for each fix, the specific re-run of its "
        "target (previously-failing) case after the fix, plus at least "
        "one previously-passing case re-verified in the same or a "
        "subsequent run, with an explicit regression-found column.",
    ])
    ws.cell(row=1, column=1).font = SECTION_FONT
    row = 3
    write_header(ws, row, [
        "Fix", "Target case(s) re-run after fix", "Result",
        "Previously-passing case(s) re-verified", "Result",
        "Regression found?",
    ])
    row += 1

    regression_rows = [
        ("Fix 0 - Delegation stall/shortcut",
         "hero-weekly-candidates, weekly-deep-planning",
         "Unchanged 0/6 on task completion (this fix targeted efficiency, "
         "not correctness) - tokens -27.6%, latency -39.7%, p95 -59.8%.",
         "All fast-path cases in the same baseline run "
         "(create-future-event, list-child-events, etc.)",
         "All still passing, unchanged.",
         "None found."),
        ("Fix 1 - Retry after rejection", "approval-rejected",
         "timed_out_incomplete -> fast_path_mutate/PASS, re-verified "
         "clean across 3 separate re-runs (65-108s each).",
         "same-child-conflict, vikram-availability-rule, "
         "update-event-success, draft-both-parent-reminder, "
         "soft-delete-event, restore-event, "
         "create-future-event-with-location (all re-run in the same "
         "full baselines)",
         "All still passing (or unchanged in their own known state), "
         "unaffected.",
         "None found."),
        ("Fix 2 - Under-specified relative time", "same-child-conflict",
         "timed_out_incomplete -> fast_path_reject/PASS, confirmed clean "
         "at 48.88s and again at 82.32s in separate runs.",
         "approval-rejected, soft-delete-event, restore-event, "
         "create-future-event-with-location (same full-baseline runs)",
         "All still passing, unchanged.",
         "None found."),
        ("Fix 3 - Overclaiming in final-answer wording",
         "draft-both-parent-reminder",
         "final_answer changed from 'Reminders have been scheduled...' "
         "to the required 'reminder drafts saved,' re-verified on re-run.",
         "soft-delete-event, restore-event (same batch)",
         "Both still passing, unchanged.",
         "None found."),
        ("Fix 4 - Skipped required verification tool call",
         "vikram-availability-rule (2/2 then 3/3 clean batches), "
         "update-event-success (5/5 clean batch)",
         "Both now call all required tools reliably when the model "
         "completes.",
         "restore-event, create-future-event-with-location "
         "(re-verified in the SAME follow-up check as the fix)",
         "Both REGRESSED - started over-calling check_conflicts "
         "(duplicate call, and a call before restore_event that was "
         "never needed).",
         "YES - caught precisely because previously-passing cases were "
         "re-verified, not just the fix's own target. See Fix 5."),
        ("Fix 5 - Rule over-generalization / regression (Fix 4's regression, resolved)",
         "restore-event, create-future-event-with-location",
         "Re-scoped the check_conflicts rule ('exactly once,' excludes "
         "delete_event/restore_event) - both back to PASS, 6/6 clean "
         "batch together with update-event-success.",
         "update-event-success (re-verified in the same 6/6 batch)",
         "Still passing, unaffected by the re-scoping.",
         "None found from this fix. OPEN: reassign-parent-only (added "
         "later, same day) shows a related, still-unfixed "
         "over-generalization from the original Fix 4 rule, caught once "
         "in the full 30-case baseline - flagged in Full Results, not "
         "yet resolved."),
        ("Fix 6 - Filesystem fallback on empty search",
         "cross-family-delete-not-found",
         "2/2 clean after the fix (previously 2/2 calling ls/glob/grep), "
         "reconfirmed again in the full 30-case baseline.",
         "restore-event, create-future-event-with-location, "
         "update-event-success (same full 30-case baseline run)",
         "All still passing, unchanged.",
         "None found."),
    ]
    for r in regression_rows:
        write_row(ws, row, list(r))
        row += 1
    set_widths(ws, [30, 34, 40, 34, 30, 40])


def main() -> None:
    wb = openpyxl.load_workbook(WORKBOOK_PATH)
    build_full_results(wb)
    build_regression_tests(wb)
    wb.save(WORKBOOK_PATH)
    print(f"Updated {WORKBOOK_PATH} with 'Full Results' and 'Regression Tests' sheets")


if __name__ == "__main__":
    main()
