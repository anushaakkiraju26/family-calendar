import json
from pathlib import Path


def test_evaluation_matrix_has_required_unique_cases():
    path = Path(__file__).resolve().parents[1] / "evaluations" / "cases.json"
    cases = json.loads(path.read_text())
    assert len(cases) >= 10
    assert len({case["id"] for case in cases}) == len(cases)
    assert all(
        {"id", "prompt", "expected_tools", "approval", "expected_outcome"}
        <= set(case)
        for case in cases
    )
    assert any(case.get("failure_path") for case in cases)
