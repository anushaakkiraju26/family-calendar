"""Shared case metadata for Week 4 evaluation tooling.

Single source of truth for scenario_type, severity, and
target_workflow_category, imported by both tools/build_eval_tracker.py
(spreadsheet) and evaluations/run_baseline_eval.py (live runner) so the two
never drift apart.
"""
from __future__ import annotations

# scenario_type per the Week 4 handout's happy/edge/known-failure/adversarial
# mix. Reflects what each case was *designed* to test, not observed results.
SCENARIO_TYPES = {
    "create-future-event": "happy_path",
    "reject-past-event": "known_failure",
    "list-child-events": "happy_path",
    "same-child-conflict": "edge_case",
    "different-children-overlap": "edge_case",
    "same-parent-conflict": "edge_case",
    "soft-delete-event": "happy_path",
    "restore-event": "happy_path",
    "draft-both-parent-reminder": "happy_path",
    "reject-past-reminder": "edge_case",
    "ambiguous-event": "edge_case",
    "approval-rejected": "edge_case",
    "family-isolation": "edge_case",
    "provider-rate-limit": "edge_case",
    "weekly-deep-planning": "known_failure",
    "school-event-overlap": "edge_case",
    "school-early-dismissal": "edge_case",
    "hero-weekly-candidates": "known_failure",
    "vikram-availability-rule": "edge_case",
    "stale-weekly-option": "edge_case",
    "family-outing-weekend": "happy_path",
    "untrusted-event-title-injection": "adversarial",
    "create-future-event-with-location": "happy_path",
    "list-family-next-week": "happy_path",
    "update-event-success": "happy_path",
    "list-reminder-drafts": "happy_path",
    "reassign-parent-only": "happy_path",
    "cross-family-delete-not-found": "edge_case",
    "list-events-empty-family": "edge_case",
    "draft-single-parent-reminder": "happy_path",
}

# Zero-tolerance real-world-harm cases: scored and reported separately at a
# 100% bar regardless of the metric's own aggregate pass bar. Everything not
# listed here defaults to "standard" (normal aggregate slack applies).
SEVERITY_CRITICAL = {
    "same-child-conflict",
    "same-parent-conflict",
    "vikram-availability-rule",
    "approval-rejected",
    "stale-weekly-option",
    "family-outing-weekend",
    "untrusted-event-title-injection",
}


def severity_of(case_id: str) -> str:
    return "critical" if case_id in SEVERITY_CRITICAL else "standard"


# The classification target for the coordinator's routing decision - which
# path SHOULD it take for this request. Ground truth for both the Step 1
# classification report and the live runner's correctness check.
TARGET_WORKFLOW = {
    "create-future-event": "fast_path_mutate",
    "reject-past-event": "fast_path_reject",
    "list-child-events": "fast_path_read",
    "same-child-conflict": "fast_path_reject",
    "different-children-overlap": "fast_path_mutate",
    "same-parent-conflict": "fast_path_reject",
    "soft-delete-event": "fast_path_mutate",
    "restore-event": "fast_path_mutate",
    "draft-both-parent-reminder": "fast_path_mutate",
    "reject-past-reminder": "fast_path_reject",
    "ambiguous-event": "ambiguous_clarify",
    "approval-rejected": "fast_path_mutate",
    "family-isolation": "fast_path_read",
    "provider-rate-limit": "fast_path_read",
    "weekly-deep-planning": "deep_weekly_workflow",
    "school-event-overlap": "fast_path_reject",
    "school-early-dismissal": "deep_weekly_workflow",
    "hero-weekly-candidates": "deep_weekly_workflow",
    "vikram-availability-rule": "fast_path_reject",
    "stale-weekly-option": "fast_path_reject",
    "family-outing-weekend": "outing_workflow",
    "untrusted-event-title-injection": "fast_path_read",
    "create-future-event-with-location": "fast_path_mutate",
    "list-family-next-week": "fast_path_read",
    "update-event-success": "fast_path_mutate",
    "list-reminder-drafts": "fast_path_read",
    "reassign-parent-only": "fast_path_mutate",
    "cross-family-delete-not-found": "fast_path_reject",
    "list-events-empty-family": "fast_path_read",
    "draft-single-parent-reminder": "fast_path_mutate",
}

# Cases where the eval harness should auto-reject the pending approval
# instead of the default auto-approve, to exercise the rejection path.
APPROVAL_OVERRIDES = {
    "approval-rejected": "reject",
}
