import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluations"))

from eval_common import SCENARIO_TYPES  # noqa: E402


def test_evaluation_matrix_has_required_unique_cases():
    path = Path(__file__).resolve().parents[1] / "evaluations" / "cases.json"
    cases = json.loads(path.read_text())
    assert len(cases) >= 10
    assert len({case["id"] for case in cases}) == len(cases)
    assert all(
        {"id", "evaluation_set", "prompt", "expected_tools", "expected_tool_order", "approval", "expected_outcome"}
        <= set(case)
        for case in cases
    )
    assert any(case.get("negative_scenario") for case in cases)
    assert all(set(case["expected_tool_order"]) <= set(case["expected_tools"]) for case in cases)
    assert any(case["id"] == "untrusted-event-title-injection" for case in cases)
    assert {case["evaluation_set"] for case in cases} == {
        "core_golden", "extended_regression"
    }
    core = [case for case in cases if case["evaluation_set"] == "core_golden"]
    assert len(core) == 20
    assert Counter(SCENARIO_TYPES[case["id"]] for case in core) == {
        "happy_path": 10,
        "edge_case": 6,
        "known_failure": 3,
        "adversarial": 1,
    }
    same_child = next(case for case in core if case["id"] == "same-child-conflict")
    assert same_child["expected_tools"] == ["list_events", "check_conflicts"]
    assert same_child["expected_tool_order"] == ["list_events", "check_conflicts"]
