"""Convert evaluations/cases.json into a clean, single-sheet spreadsheet -
one row per case, enriched with the scenario_type/severity/
target_workflow_category metadata from eval_common.py, matching the format
already used in the Golden Dataset tab of week4_eval_tracker_Anusha.xlsx.

Run: python tools/build_cases_spreadsheet.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "evaluations"))
from eval_common import SCENARIO_TYPES, TARGET_WORKFLOW, severity_of  # noqa: E402

CASES_PATH = PROJECT_ROOT / "evaluations" / "cases.json"
OUTPUT_PATH = PROJECT_ROOT / "evaluations" / "cases.xlsx"

HEADER_FILL = PatternFill(start_color="1F2A44", end_color="1F2A44", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)
WRAP = Alignment(wrap_text=True, vertical="top")


def main() -> None:
    cases = json.loads(CASES_PATH.read_text())

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Golden Dataset"

    headers = [
        "case_id", "evaluation_set", "scenario_type", "severity",
        "target_workflow_category", "prompt", "expected_tools",
        "expected_tool_order", "approval", "expected_outcome",
        "is_negative_scenario",
    ]
    for col, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = WRAP

    for row, case in enumerate(cases, start=2):
        case_id = case["id"]
        values = [
            case_id,
            case.get("evaluation_set", ""),
            SCENARIO_TYPES.get(case_id, ""),
            severity_of(case_id),
            TARGET_WORKFLOW.get(case_id, ""),
            case.get("prompt", ""),
            ", ".join(case.get("expected_tools", [])) or "(none)",
            " > ".join(case.get("expected_tool_order", [])) or "N/A",
            case.get("approval", ""),
            case.get("expected_outcome", ""),
            "yes" if case.get("negative_scenario") else "no",
        ]
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.alignment = WRAP

    widths = [34, 20, 14, 10, 24, 60, 34, 34, 30, 60, 10]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"

    # Summary sheet: core scenario mix + case counts, mirroring the Golden
    # Dataset tab's own summary block.
    summary = wb.create_sheet("Summary")
    core = [c for c in cases if c.get("evaluation_set") == "core_golden"]
    extended = [c for c in cases if c.get("evaluation_set") == "extended_regression"]
    from collections import Counter
    mix = Counter(SCENARIO_TYPES.get(c["id"], "") for c in core)
    rows = [
        ["Total cases", len(cases)],
        ["core_golden", len(core)],
        ["extended_regression", len(extended)],
        [],
        ["core_golden scenario mix:"],
    ]
    for scenario_type in ("happy_path", "edge_case", "known_failure", "adversarial"):
        count = mix.get(scenario_type, 0)
        pct = round(100 * count / len(core)) if core else 0
        rows.append([scenario_type, f"{count} cases ({pct}%)"])
    for r_idx, row_values in enumerate(rows, start=1):
        for c_idx, value in enumerate(row_values, start=1):
            summary.cell(row=r_idx, column=c_idx, value=value)
    summary.column_dimensions["A"].width = 24
    summary.column_dimensions["B"].width = 24

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUTPUT_PATH)
    print(f"Wrote {OUTPUT_PATH} ({len(cases)} cases)")


if __name__ == "__main__":
    main()
