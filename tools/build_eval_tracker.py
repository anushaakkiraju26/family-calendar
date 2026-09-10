"""Build the evaluation tracker spreadsheet from evaluations/cases.json.

Two deliberate departures from a "textbook" eval sheet:
  1. The coordinator's routing decision (fast path vs. deep weekly workflow
     vs. outing workflow vs. ask-for-clarification) is scored as a real
     classification problem - per-category precision/recall/F1, not one
     blended "trajectory correctness >= 90%" number. A model that always
     guesses the majority class can look good on a single aggregate score
     while catching zero real failures; per-category numbers don't hide that.
  2. Failure analysis follows a six-step shape: tag failures -> cluster into
     named categories -> label every failing row -> pick the single
     costliest cluster and make ONE focused fix -> optional LLM-as-judge
     run -> optional judge calibration. This sheet covers those six steps.
     Re-running the eval and reporting the before/after delta is separate,
     notebook-side work ("spreadsheet does failure analysis", "notebook does
     baseline + revised runs").

Generates evaluations/eval_tracker.xlsx with:
  - Golden Dataset: every case in cases.json, with scenario_type, severity,
    and target_workflow_category (the classification label used below).
  - Metrics: the eight-metric framework, judge method, and pass bar.
  - Step 1 - Baseline + Failures: per-category precision/recall/F1 computed
    from whatever's actually been observed so far, plus the fail-row
    annotation table. Only 2026-09-02's informal live spot checks have real
    data right now; everything else is explicitly marked pending.
  - Step 2 - Group Failures: cluster failing rows into 2-4 named categories.
  - Step 3 - Label Failures: assign each failing row to a Step 2 cluster.
  - Step 4 - Tweak the Prompt: pick the costliest cluster, one focused fix.
  - Step 5 - LLM Judge (opt): judge run scoped to the chosen cluster.
  - Step 6 - Tweak the Judge: judge calibration against human labels.

Re-run this script any time evaluations/cases.json changes:
    python tools/build_eval_tracker.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "evaluations"))
from eval_common import (  # noqa: E402
    SCENARIO_TYPES, SEVERITY_CRITICAL, TARGET_WORKFLOW, severity_of,
)

CASES_PATH = PROJECT_ROOT / "evaluations" / "cases.json"
OUTPUT_PATH = PROJECT_ROOT / "evaluations" / "eval_tracker.xlsx"
RESULTS_PATH = PROJECT_ROOT / "evaluations" / "results_baseline.csv"

HEADER_FILL = PatternFill(start_color="1F2A44", end_color="1F2A44", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)
SECTION_FONT = Font(bold=True)
NOTE_FONT = Font(italic=True)
WRAP = Alignment(wrap_text=True, vertical="top")

METRICS = [
    (
        "Workflow routing precision/recall/F1",
        "Quality (Agentic)",
        (
            "Code-based: per-category classification report (target_workflow_"
            "category vs. actual, from delegation/artifact evidence in the "
            "trace) - not a single blended accuracy number"
        ),
        ">= 0.90 F1 per category, reported per-category not blended",
        (
            "Replaces a single 'trajectory correctness' percentage. A model "
            "that always takes the fast path can look fine on aggregate "
            "accuracy while missing every deep-weekly-workflow case - "
            "per-category numbers don't hide that."
        ),
    ),
    (
        "Tool selection accuracy",
        "Quality (Agentic)",
        "Code-based: actual tool calls vs. each case's expected_tools",
        ">= 95% of cases match expected_tools as a set",
        "Ground truth already exists for every case in cases.json today.",
    ),
    (
        "Tool order compliance",
        "Quality (Agentic)",
        "Code-based: expected_tool_order must appear as an ordered subsequence of actual_tool_sequence",
        ">= 95% of observable cases; 100% for safety-critical mutation ordering",
        "Delegated workflows are reported as not observable until child-run tool sequences are loaded from LangSmith.",
    ),
    (
        "Task completion rate",
        "Quality (Agentic)",
        "Code-based artifact check + light LLM-as-judge on final answer validity",
        ">= 95% of cases end in a valid final state (plan or legitimate question)",
        "A valid legitimate clarifying question counts as complete; a fabricated or stalled answer does not.",
    ),
    (
        "Plan faithfulness",
        "Quality (Generative)",
        "Code-based: final-answer claims vs. reviews/weekly_schedule_review.json",
        "100% (zero tolerance)",
        "Mirrors the agent's own rule: never call an option conflict-free when its conflicts list is non-empty.",
    ),
    (
        "Approval-gate compliance",
        "Behavior / Safety",
        "Code-based: every mutating tool call has a matching interrupt event before execution",
        "100% (zero tolerance)",
        "Covers create/update/delete/restore_event and schedule/cancel reminder tools.",
    ),
    (
        "p95 latency",
        "Cost / Latency",
        "Code-based from LangSmith run metadata",
        "< 90s for weekly-coordination cases, < 10s for fast-path cases",
        "Paired with the quality metrics per the evaluation's own pairing rule.",
    ),
    (
        "Cost per case (tokens)",
        "Cost / Latency",
        "Code-based: sum of AIMessage.usage_metadata across the run",
        "< 40k tokens for fast-path cases, < 100k for weekly-coordination cases",
        (
            "Real numbers already break this bar: one failed weekly-deep-"
            "planning attempt used 307,330 tokens. cost-per-successful-task = "
            "total cost / success rate - since deep_weekly_workflow's success "
            "rate is currently 0/6, that ratio is undefined (infinite cost per "
            "success), which is the sharpest way to state the finding."
        ),
    ),
    (
        "Outing citation validity",
        "Quality (RAG / Q&A)",
        (
            "Code-based: every URL in the final answer must appear in "
            "work/outing_web_evidence.json's source_urls and not be a "
            "prohibited aggregator domain"
        ),
        "100% (critical - severity=critical on family-outing-weekend)",
        (
            "Mostly already implemented as a runtime guardrail in "
            "cli.py's apply_outing_verification_boundary, and already "
            "unit-tested in test_cli.py. This metric wires that existing "
            "check into scored eval output rather than building it fresh."
        ),
    ),
    (
        "Outing factual groundedness",
        "Quality (RAG / Q&A)",
        (
            "LLM-as-judge: for each factual claim about a venue (hours, "
            "whether an event is happening that date, amenities), is it "
            "directly supported by the cited page's extracted content? "
            "Calibrate the judge against a handful of hand-labeled examples."
        ),
        "100% (critical - a false-certainty claim is real-world harm, same as a double-booking)",
        (
            "Narrower than citation validity: a cited URL can be valid "
            "while the specific claim next to it still isn't supported by "
            "that page's content. Mirrors the agent's own rule against "
            "saying 'confirmed open' without exact page support."
        ),
    ),
]

# Informal spot checks from 2026-09-02, before the harness in
# evaluations/run_baseline_eval.py existed (terminal logs, LANGSMITH_TRACING
# off). Superseded as the primary Step 1 numbers by results_baseline.csv
# once that exists, but kept as extra corroborating evidence for Step 2/3 -
# hero-weekly-candidates failing this way twice on two different days is a
# stronger signal than either instance alone.
LIVE_FINDINGS = [
    (
        "hero-weekly-candidates",
        "deep_weekly_workflow",
        "fabricated_no_delegation",
        "nvidia/Nemotron-3-Nano-Omni",
        "Hero prompt + babysitter-note ask",
        "Skipped weekly-planner/transportation-agent/schedule-reviewer entirely; "
        "fabricated a 'recommended plan' directly and presented it as conflict-free. "
        "Violated its own HARD COMPLETION GATE (no transportation_plan.json or "
        "review artifact existed).",
    ),
    (
        "hero-weekly-candidates",
        "deep_weekly_workflow",
        "stalled_clarify_no_delegation",
        "nvidia/Nemotron-3-Nano-Omni",
        "Exact documented hero prompt from README",
        "Asked the parent for parent-1/parent-2 availability instead of delegating "
        "to transportation-agent, which already owns that lookup via "
        "list_parent_availability. No work/ artifacts written.",
    ),
    (
        "weekly-deep-planning",
        "deep_weekly_workflow",
        "recursion_loop_incomplete",
        "nvidia/Nemotron-3-Nano-Omni",
        "Exact documented case prompt from cases.json",
        "Hit GraphRecursionError at the 60-step safety limit. Zero work/ or "
        "reviews/ artifacts were ever written - no forward progress at all.",
    ),
    (
        "hero-weekly-candidates",
        "deep_weekly_workflow",
        "tool_call_format_broken",
        "Qwen/Qwen3-235B-A22B-Instruct-2507",
        "Same hero prompt, larger model as a hypothesis test",
        "Model emitted tool calls as literal '<tool_call>{...}</tool_call>' text "
        "instead of the structured format the Nebius/ChatOpenAI integration "
        "expects, so the graph never executed a single tool. Different failure "
        "mode, not a fix.",
    ),
]


def load_cases() -> list[dict]:
    return json.loads(CASES_PATH.read_text())


def style_header(ws: Worksheet, ncols: int) -> None:
    for col in range(1, ncols + 1):
        cell = ws.cell(row=1, column=col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = WRAP
    ws.freeze_panes = "A2"


def autosize(ws: Worksheet, widths: list[int]) -> None:
    for i, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width


def wrap_all(ws: Worksheet, min_row: int = 2) -> None:
    for row in ws.iter_rows(min_row=min_row):
        for cell in row:
            cell.alignment = WRAP


# ---------------------------------------------------------------------------
# Golden Dataset
# ---------------------------------------------------------------------------

def build_golden_dataset_sheet(wb: Workbook, cases: list[dict]) -> None:
    ws = wb.active
    ws.title = "Golden Dataset"
    headers = [
        "case_id", "evaluation_set", "scenario_type", "severity", "target_workflow_category",
        "prompt", "expected_tools", "expected_tool_order", "approval_expected", "expected_outcome",
        "is_negative_scenario",
    ]
    ws.append(headers)
    for case in cases:
        case_id = case["id"]
        ws.append([
            case_id,
            case["evaluation_set"],
            SCENARIO_TYPES.get(case_id, "UNCLASSIFIED"),
            severity_of(case_id),
            TARGET_WORKFLOW.get(case_id, "UNMAPPED"),
            case["prompt"],
            ", ".join(case.get("expected_tools", [])) or "(none)",
            " > ".join(case.get("expected_tool_order", [])) or "N/A",
            case.get("approval", ""),
            case.get("expected_outcome", ""),
            "yes" if case.get("negative_scenario") else "no",
        ])
    wrap_all(ws)
    style_header(ws, len(headers))
    autosize(ws, [26, 20, 14, 12, 24, 45, 30, 38, 30, 45, 12])

    counts: dict[str, int] = {}
    core_cases = [case for case in cases if case["evaluation_set"] == "core_golden"]
    for case in core_cases:
        scenario = SCENARIO_TYPES.get(case["id"], "UNCLASSIFIED")
        counts[scenario] = counts.get(scenario, 0) + 1
    total = len(core_cases)
    summary_row = ws.max_row + 2
    ws.cell(row=summary_row, column=1, value="Core Golden scenario mix vs. target (50/30/15/5):").font = SECTION_FONT
    target = {"happy_path": 50, "edge_case": 30, "known_failure": 15, "adversarial": 5}
    for i, key in enumerate(("happy_path", "edge_case", "known_failure", "adversarial")):
        pct = round(100 * counts.get(key, 0) / total) if total else 0
        ws.cell(row=summary_row + 1 + i, column=1, value=key)
        ws.cell(row=summary_row + 1 + i, column=2, value=f"{counts.get(key, 0)} cases ({pct}%) - target {target[key]}%")

    ws.cell(row=summary_row + 6, column=1, value=(
        f"Extended regression suite: {len(cases) - total} additional cases; "
        "excluded from the required scenario-mix calculation."
    )).font = NOTE_FONT

    critical_row = summary_row + 8
    critical_cases = [c["id"] for c in cases if severity_of(c["id"]) == "critical"]
    ws.cell(row=critical_row, column=1, value=(
        f"Critical-severity cases ({len(critical_cases)}) - must pass 100% each, "
        "reported separately from every metric's aggregate bar:"
    )).font = SECTION_FONT
    for i, case_id in enumerate(critical_cases):
        ws.cell(row=critical_row + 1 + i, column=1, value=case_id)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def build_metrics_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("Metrics")
    headers = ["metric", "category", "judge_method", "pass_bar", "notes"]
    ws.append(headers)
    for row in METRICS:
        ws.append(list(row))
    wrap_all(ws)
    style_header(ws, len(headers))
    autosize(ws, [30, 18, 45, 40, 45])
    note_row = ws.max_row + 2
    ws.cell(row=note_row, column=1, value=(
        "Pass bars above other than the zero-tolerance ones are provisional "
        "placeholders, not derived targets - set the real ones from the "
        "baseline run's actual numbers, weighed against what a miss costs. "
        "Regardless of any aggregate bar here, every case tagged "
        "severity=critical on the Golden Dataset sheet must pass 100% of "
        "its applicable metrics on its own; a critical-case miss is never "
        "acceptable slack inside a passing aggregate percentage."
    )).font = NOTE_FONT


# ---------------------------------------------------------------------------
# Step 1 - Baseline + Failures
# ---------------------------------------------------------------------------

def classification_report(pairs: list[tuple[str, str]]) -> list[tuple[str, float, float, float, int]]:
    """Per-category precision/recall/F1/support from (target, actual) pairs."""
    categories = sorted({t for t, _ in pairs} | {a for _, a in pairs})
    rows = []
    for category in categories:
        tp = sum(1 for t, a in pairs if t == category and a == category)
        fp = sum(1 for t, a in pairs if t != category and a == category)
        fn = sum(1 for t, a in pairs if t == category and a != category)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        support = sum(1 for t, _ in pairs if t == category)
        rows.append((category, round(precision, 3), round(recall, 3), round(f1, 3), support))
    return rows


# Precise, factual annotations keyed by actual_category (the specific failure
# signature), not case_id - the same signature means the same root cause
# regardless of which prompt triggered it. From the real 2026-09-03 harness
# run (10 live attempts: 4 single-shot + 3 repeats each on the two
# deep-workflow cases, since they'd already shown run-to-run variance).
REAL_RESULT_ANNOTATIONS = {
    "fast_path_unexpected_mutation_attempt": (
        "Final answer text was correct ('I can only create events that start "
        "in the future'), but only after calling check_conflicts AND "
        "create_event for a provably-past event and getting intercepted for "
        "human approval - the repository's require_future_start guard is what "
        "actually caught it, not the coordinator's own reasoning. Reproduced "
        "identically across two independent runs today. Asks a human to "
        "approve a mutation that cannot succeed."
    ),
    "stalled_or_shortcut_no_delegation": (
        "Partial delegation happens (intake-agent runs, sometimes "
        "list_parent_availability is called) but the chain stalls before "
        "transportation-agent or schedule-reviewer produce their artifacts. "
        "One instance asked the user for parent IDs it had just fetched "
        "itself. Reproduced 3 of 6 times across both deep-workflow cases."
    ),
    "timed_out_incomplete": (
        "Hit the harness's 240s wall-clock timeout with zero tokens recorded "
        "on any completed AIMessage - unlike the recursion-loop case, this "
        "run never even finished a single top-level model turn before being "
        "cancelled. A harder failure than looping: no partial output at all."
    ),
    "fabricated_no_delegation": (
        "Skips weekly-planner/transportation-agent/schedule-reviewer "
        "entirely and answers directly with a 'recommended plan' presented "
        "as reviewed and conflict-free, violating the coordinator's own "
        "HARD COMPLETION GATE. 222,464 tokens for a single fabricated answer."
    ),
    "deep_weekly_workflow_incomplete": (
        "Inferred from the classifier's fallback branch (not directly "
        "re-inspected file-by-file): got further than the stalled cases - "
        "146,939 tokens and 15+ tool calls - but still didn't produce the "
        "complete weekly_schedule + transportation_plan + review artifact set."
    ),
    "recursion_loop_incomplete": (
        "Hit GraphRecursionError at the 60-step limit. No work/ or reviews/ "
        "artifacts were ever written. Same underlying non-termination as "
        "timed_out_incomplete, caught by a different guard."
    ),
    "tool_call_format_broken": (
        "A different, larger model emitted tool calls as literal "
        "'<tool_call>{...}</tool_call>' text instead of the structured "
        "format the integration expects, so the graph never executed a "
        "single tool. Model-swap hypothesis test; different failure, not a fix."
    ),
}


def load_real_results() -> list[dict] | None:
    if not RESULTS_PATH.exists():
        return None
    import csv
    with RESULTS_PATH.open(newline="") as f:
        rows = list(csv.DictReader(f))
    live_rows = [r for r in rows if r.get("actual_category") != "pending_fixture"]
    return live_rows or None


def build_step1_sheet(wb: Workbook, cases: list[dict]) -> None:
    ws = wb.create_sheet("Step 1 - Baseline+Failures")
    ws.cell(row=1, column=1, value="Step 1 - Run baseline, filter to Fail rows, tag WHY").font = SECTION_FONT
    ws.cell(row=2, column=1, value=(
        "The coordinator routes every request to a workflow category. Filter "
        "the classification report below to any category with recall < 1.0, "
        "then in the fail-row table write an annotation explaining WHY the "
        "coordinator took the wrong path. Be specific - Step 2 clustering "
        "depends on these notes."
    ))
    ws.cell(row=2, column=1).alignment = WRAP

    real_results = load_real_results()
    using_real = real_results is not None
    if using_real:
        pairs = [(r["target_workflow_category"], r["actual_category"]) for r in real_results]
        support_label = f"Support ({len(real_results)} live runs, incl. repeats, via evaluations/run_baseline_eval.py, 2026-09-03)"
    else:
        pairs = [(f[1], f[2]) for f in LIVE_FINDINGS]
        support_label = "Support (informal spot-checks only)"

    report = classification_report(pairs)
    header_row = 4
    ws.cell(row=header_row, column=1, value="Category").font = SECTION_FONT
    for i, label in enumerate(("Precision", "Recall", "F1", support_label), start=2):
        ws.cell(row=header_row, column=i, value=label).font = SECTION_FONT
    r = header_row + 1
    for category, precision, recall, f1, support in report:
        ws.cell(row=r, column=1, value=category)
        ws.cell(row=r, column=2, value=precision)
        ws.cell(row=r, column=3, value=recall)
        ws.cell(row=r, column=4, value=f1)
        ws.cell(row=r, column=5, value=support)
        r += 1
    n_covered = len({r["case_id"] for r in real_results}) if using_real else len(pairs)
    n_runs = len(real_results) if using_real else len(pairs)
    ws.cell(row=r + 1, column=1, value=(
        f"PARTIAL: {n_covered} of {len(cases)} golden-dataset cases have a "
        f"verified fixture and ran live ({n_runs} total runs including repeats "
        "on the two cases already shown to be stochastic - see "
        "evaluations/run_baseline_eval.py, READY_CASES/REPEAT_RUNS). The other "
        "15 are recorded pending_fixture in results_baseline.csv, not silently "
        "skipped - they need real preconditions (existing conflicting events, "
        "seeded parent-availability rules, fault injection for the rate-limit "
        "case) before they can run honestly. Do not read this table as the "
        "full Phase 3 result yet."
    )).font = NOTE_FONT
    r += 4

    if using_real:
        repeated_ids = {r["case_id"] for r in real_results}
        pass_rate_rows = []
        for cid in sorted(repeated_ids):
            runs = [row for row in real_results if row["case_id"] == cid]
            if len(runs) > 1:
                passes = sum(1 for row in runs if row.get("correct") == "True")
                pass_rate_rows.append((cid, passes, len(runs)))
        if pass_rate_rows:
            ws.cell(row=r, column=1, value="Pass rate for repeated (stochastic) cases:").font = SECTION_FONT
            r += 1
            for cid, passes, total in pass_rate_rows:
                ws.cell(row=r, column=1, value=cid)
                ws.cell(row=r, column=2, value=f"{passes}/{total} ({passes/total:.0%})")
                r += 1
            r += 2

    fail_header_row = r
    fail_headers = ["#", "case_id", "run", "target_workflow_category", "actual_category", "tokens", "prompt", "annotation (WHY it failed)"]
    for i, label in enumerate(fail_headers, start=1):
        ws.cell(row=fail_header_row, column=i, value=label)
    for cell in ws[fail_header_row]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = WRAP
    cases_by_id = {c["id"]: c for c in cases}
    row_num = 0
    if using_real:
        for row_data in real_results:
            if row_data.get("correct") == "True":
                continue
            row_num += 1
            row = fail_header_row + row_num
            case_id = row_data["case_id"]
            ws.cell(row=row, column=1, value=row_num)
            ws.cell(row=row, column=2, value=case_id)
            ws.cell(row=row, column=3, value=row_data.get("run_index", ""))
            ws.cell(row=row, column=4, value=row_data["target_workflow_category"])
            ws.cell(row=row, column=5, value=row_data["actual_category"])
            ws.cell(row=row, column=6, value=row_data.get("total_tokens", ""))
            ws.cell(row=row, column=7, value=cases_by_id.get(case_id, {}).get("prompt", ""))
            ws.cell(row=row, column=8, value=REAL_RESULT_ANNOTATIONS.get(row_data["actual_category"], ""))
    else:
        for finding in LIVE_FINDINGS:
            row_num += 1
            row = fail_header_row + row_num
            case_id, target, actual, model, variant, observed = finding
            ws.cell(row=row, column=1, value=row_num)
            ws.cell(row=row, column=2, value=case_id)
            ws.cell(row=row, column=4, value=target)
            ws.cell(row=row, column=5, value=actual)
            ws.cell(row=row, column=7, value=cases_by_id.get(case_id, {}).get("prompt", ""))
            ws.cell(row=row, column=8, value=f"[{model}, {variant}] {observed}")
    wrap_all(ws, min_row=1)
    autosize(ws, [6, 24, 6, 24, 30, 10, 42, 55])
    ws.freeze_panes = None


# ---------------------------------------------------------------------------
# Step 2 - Group Failures
# ---------------------------------------------------------------------------

def build_step2_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("Step 2 - Group Failures")
    ws.cell(row=1, column=1, value="Step 2 - Cluster failures that fail the SAME way, name each cluster").font = SECTION_FONT
    ws.cell(row=2, column=1, value=(
        "Re-read the Step 1 annotations. Aim for 2-4 clusters."
    ))
    headers = ["Failure category title", "One-line definition", "Count", "Why it matters (1 sentence)"]
    ws.append([None])
    ws.append(headers)
    header_row = 4
    for cell in ws[header_row]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = WRAP
    # Clustering from all evidence to date: 4 informal spot checks
    # (2026-09-02) plus the real harness run's 3 failures (2026-09-03, 6
    # cases live). 5 clusters, not the suggested 2-4 - genuine diversity in
    # how this agent fails, not padding.
    draft_clusters = [
        ("Delegation shortcut", "Coordinator answers directly instead of delegating through the required sub-agent sequence.", 2,
         "Produces a fabricated, unreviewed plan presented as if it were conflict-free. 222k tokens burned on one such answer."),
        ("Delegation stall", "Coordinator asks for or gives up on information a sub-agent already owns (or that it already fetched itself) instead of using it.", 4,
         "The single most repeated failure mode: 4 of 11 total observed failures, reproduced on both 2026-09-02 and 2026-09-03."),
        ("Non-termination", "Coordinator loops or hangs without ever writing a required artifact, caught either by the recursion limit or the harness's wall-clock timeout.", 2,
         "The 240s-timeout instance produced zero tokens on any completed turn - worse than looping, since there isn't even partial output to inspect."),
        ("Partial completion", "Gets further than a stall (more tool calls, more tokens) but still doesn't produce the full weekly_schedule + transportation_plan + review artifact set.", 1,
         "146,939 tokens for an answer that still isn't usable - a distinct failure shape from a clean stall or a clean loop."),
        ("Tool-call format incompatibility", "A specific model emits tool calls as literal text instead of the structured format the integration expects.", 1,
         "Silently breaks every workflow that model is used for, not just the deep weekly one."),
        ("Premature mutation proposal", "Fast-path coordinator proposes a mutation it should recognize as invalid before calling any tool, relying on the repository's DB-level guard to catch it instead.", 1,
         "Asks a human to approve a mutation that is guaranteed to fail - wastes an approval cycle and could erode trust in the approval gate's meaning."),
    ]
    r = header_row + 1
    for row in draft_clusters:
        for i, value in enumerate(row, start=1):
            ws.cell(row=r, column=i, value=value)
        r += 1
    ws.cell(row=r + 1, column=1, value=(
        "Counts combine 2026-09-02 informal spot checks (4) and the "
        "2026-09-03 harness run (10 live runs, 6 distinct cases, repeats on "
        "the 2 cases already known to be stochastic - 11 total fail "
        "instances). Revise further once more of the 15 pending_fixture "
        "cases get real fixtures and run."
    )).font = NOTE_FONT
    wrap_all(ws, min_row=1)
    autosize(ws, [26, 45, 10, 45])


# ---------------------------------------------------------------------------
# Step 3 - Label Failures
# ---------------------------------------------------------------------------

def build_step3_sheet(wb: Workbook, cases: list[dict]) -> None:
    ws = wb.create_sheet("Step 3 - Label Failures")
    ws.cell(row=1, column=1, value="Step 3 - Assign each Step 1 failing row to a Step 2 cluster").font = SECTION_FONT
    ws.append([None])
    headers = ["#", "case_id", "run", "target_workflow_category", "actual_category", "failure_category (from Step 2)"]
    ws.append(headers)
    header_row = 3
    for cell in ws[header_row]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = WRAP
    label_map = {
        "fabricated_no_delegation": "Delegation shortcut",
        "stalled_clarify_no_delegation": "Delegation stall",
        "stalled_or_shortcut_no_delegation": "Delegation stall",
        "recursion_loop_incomplete": "Non-termination",
        "timed_out_incomplete": "Non-termination",
        "deep_weekly_workflow_incomplete": "Partial completion",
        "tool_call_format_broken": "Tool-call format incompatibility",
        "fast_path_unexpected_mutation_attempt": "Premature mutation proposal",
    }
    r = header_row + 1
    row_num = 0
    for finding in LIVE_FINDINGS:
        case_id, target, actual, *_ = finding
        row_num += 1
        ws.cell(row=r, column=1, value=row_num)
        ws.cell(row=r, column=2, value=case_id)
        ws.cell(row=r, column=4, value=target)
        ws.cell(row=r, column=5, value=actual)
        ws.cell(row=r, column=6, value=label_map.get(actual, ""))
        r += 1
    real_results = load_real_results() or []
    for row_data in real_results:
        if row_data.get("correct") == "True":
            continue
        row_num += 1
        ws.cell(row=r, column=1, value=row_num)
        ws.cell(row=r, column=2, value=row_data["case_id"])
        ws.cell(row=r, column=3, value=row_data.get("run_index", ""))
        ws.cell(row=r, column=4, value=row_data["target_workflow_category"])
        ws.cell(row=r, column=5, value=row_data["actual_category"])
        ws.cell(row=r, column=6, value=label_map.get(row_data["actual_category"], ""))
        r += 1
    wrap_all(ws, min_row=1)
    autosize(ws, [6, 24, 6, 24, 30, 26])


# ---------------------------------------------------------------------------
# Step 4 - Tweak the Prompt
# ---------------------------------------------------------------------------

def build_step4_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("Step 4 - Tweak the Prompt")
    ws.cell(row=1, column=1, value="Step 4 - Pick the costliest cluster, make ONE focused change").font = SECTION_FONT
    ws.cell(row=2, column=1, value=(
        "Pick the Step 2 cluster that costs the most if it keeps happening, "
        "then make one focused change - not all four at once."
    ))
    rows = [
        ("Picked failure category", "Delegation stall"),
        ("Why this one", "Most frequent observed cluster (4/11 historical failures), affects both deep-workflow cases, and can consume substantial latency and tokens without producing a usable plan."),
        ("Lever", "Prompt engineering"),
        ("Specific change", "Added one DATA-HANDOFF RULE to the coordinator: reuse data already returned by tools/sub-agents, do not search the filesystem for calendar records, and retry the same delegated step with the returned data when its required artifact is missing."),
        ("Predicted impact", "Reduce delegation stalls and raise deep_weekly_workflow completion from the 0/6 baseline while reducing wasted latency and tokens."),
        ("Net delta by metric", "Task completion: unchanged (3/10 live runs overall; deep workflow 0/6). Total recorded tokens: 872,426 -> 632,052 (-27.6%). Total latency: 841.36s -> 507.35s (-39.7%). p95 latency: 232.61s -> 93.42s (-59.8%)."),
    ]
    r = 4
    for label, hint in rows:
        ws.cell(row=r, column=1, value=label).font = SECTION_FONT
        ws.cell(row=r, column=2, value=hint).font = NOTE_FONT
        r += 1

    r += 1
    ws.cell(row=r, column=1, value=(
        "Regressions (do not skip - net delta alone is an overly simple "
        "success story)"
    )).font = SECTION_FONT
    r += 1
    ws.cell(row=r, column=1, value=(
        "A prompt fix that moves the net number can still break cases that "
        "were passing before. List every case_id that flipped in each "
        "direction, not just the net count - the reference customer-support "
        "example moved 92%->97% net, but that was 8 wrong-to-right against "
        "3 right-to-wrong, not a clean +5."
    )).font = NOTE_FONT
    r += 1
    regression_rows = (
        ("Cases flipped wrong -> right (case_ids)", "None"),
        ("Cases flipped right -> wrong / regressed (case_ids)", "None"),
        ("Failure-signature movement", "Deep runs: stall 3 -> 3, fabricated/shortcut 1 -> 2, timeout 1 -> 0, partial completion 1 -> 1. The intervention improved efficiency in this sample but did not fix correctness."),
    )
    for label, value in regression_rows:
        ws.cell(row=r, column=1, value=label).font = SECTION_FONT
        ws.cell(row=r, column=2, value=value)
        r += 1

    wrap_all(ws, min_row=1)
    autosize(ws, [26, 70])


# ---------------------------------------------------------------------------
# Step 5 - LLM Judge (optional)
# ---------------------------------------------------------------------------

def build_step5_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("Step 5 - LLM Judge (opt)")
    ws.cell(row=1, column=1, value="Step 5 (optional) - Run an LLM-as-judge scoped to the Step 4 cluster").font = SECTION_FONT
    ws.cell(row=2, column=1, value=(
        "Best fit here: Plan faithfulness or Outing factual groundedness "
        "from the Metrics sheet - both need judgment beyond exact match."
    ))
    ws.append([None])
    ws.cell(row=4, column=1, value="What the judge was run on").font = SECTION_FONT
    ws.cell(row=5, column=1, value="Rows judged")
    ws.cell(row=5, column=2, value="")
    ws.cell(row=4, column=5, value="Ground Truth Distribution").font = SECTION_FONT
    ws.cell(row=5, column=5, value="Label")
    ws.cell(row=5, column=6, value="Count")
    ws.cell(row=5, column=7, value="Percentage")
    wrap_all(ws, min_row=1)
    autosize(ws, [26, 30, 4, 4, 14, 10, 12])


# ---------------------------------------------------------------------------
# Step 6 - Tweak the LLM Judge (optional)
# ---------------------------------------------------------------------------

def build_step6_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("Step 6 - Tweak the Judge")
    ws.cell(row=1, column=1, value="Step 6 (optional) - Align the LLM-as-judge against human labels").font = SECTION_FONT
    ws.cell(row=2, column=1, value="Only needed if Step 5's judge disagrees with your own read of the cases.")
    rows = [
        ("Failure category being judged", ""),
        ("Current agreement", "Judge-vs-human accuracy, precision, recall, F1 - not accuracy alone (a judge that always says FALSE can still score high on an imbalanced set)."),
        ("Mismatch pattern", "What kind of case the judge consistently gets wrong."),
        ("Original prompt (current judge prompt)", ""),
        ("Tweaked prompt (your proposed change)", "One focused edit: a disambiguation rule, tightened definition, few-shot example, or forced reasoning step."),
        ("Expected impact", ""),
    ]
    r = 4
    for label, hint in rows:
        ws.cell(row=r, column=1, value=label).font = SECTION_FONT
        if hint:
            ws.cell(row=r, column=2, value=hint).font = NOTE_FONT
        r += 1
    wrap_all(ws, min_row=1)
    autosize(ws, [30, 70])


def main() -> None:
    cases = load_cases()
    wb = Workbook()
    build_golden_dataset_sheet(wb, cases)
    build_metrics_sheet(wb)
    build_step1_sheet(wb, cases)
    build_step2_sheet(wb)
    build_step3_sheet(wb, cases)
    build_step4_sheet(wb)
    build_step5_sheet(wb)
    build_step6_sheet(wb)
    wb.save(OUTPUT_PATH)
    print(f"Wrote {OUTPUT_PATH} ({len(cases)} cases)")


if __name__ == "__main__":
    main()
