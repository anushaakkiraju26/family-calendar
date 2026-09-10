# Evaluation suite

`cases.json` is the golden-dataset behavior matrix. It records natural-language
requests, expected MCP tools, approval boundaries, outcomes, and negative
scenarios. A negative scenario is expected to exercise safe rejection or
recovery; it is not itself an observed agent failure.

Run the offline automated suite with:

```bash
pytest
```

The tests include real MCP subprocess discovery and invocation, a mutation that
must pause for LangGraph approval before changing SQLite, repository lifecycle
and conflict rules, reminder-draft validation, state isolation, and CLI error
formatting. The deterministic fake chat model avoids Nebius usage while preserving
the actual Deep Agent, LangGraph interrupt, MCP subprocess, and SQLite layers.

Before recording the demo, run selected prompts from `cases.json` with the live
Nebius-backed CLI and record observed tool calls and outcomes in the project
documentation. Live model behavior is intentionally not part of CI.

The family-outing case additionally requires `YDC_API_KEY`. It verifies that
calendar and school checks happen before one `you-search` MCP call, that results
retain source URLs, and that research never creates an event automatically.

## Evaluation tooling

- `eval_common.py` - shared case metadata (scenario_type, severity,
  target_workflow_category) imported by both files below, so they can't drift.
- `run_baseline_eval.py` - live runner. Only case_ids in `READY_CASES` have a
  verified fixture and actually run against the deployed agent; everything
  else is recorded `pending_fixture` in the output, not silently skipped.
  It records expected and actual tool sequences and scores expected order as
  an ordered subsequence for directly observable workflows. Delegated weekly
  and outing workflows remain unscored for order until LangSmith child-run
  inspection is implemented.
  Wraps each case in a `langsmith.trace()` span (case_id, target category,
  scenario_type, severity as metadata) rather than a second OpenTelemetry
  pipeline, since LangChain's own LangSmith tracer is already wired in via
  `LANGSMITH_TRACING=true`. Writes `results_baseline.csv`.

  ```bash
  python evaluations/run_baseline_eval.py --evaluation-set core_golden
  ```

  To diagnose selected cases without overwriting the full baseline:

  ```bash
  python evaluations/run_baseline_eval.py \
    --case-id same-child-conflict \
    --case-id approval-rejected \
    --repeat-count 1
  ```

  Targeted runs default to `results_diagnostic.csv`. Initial fast-path calls
  retain the 60-second evaluation ceiling; an approval resume gets up to 120
  seconds so a completed rejection or approval can be recorded separately from
  the initial decision latency.

- `results_baseline.csv` - one row per golden-dataset run: target vs. actual
  workflow-routing category, tool-selection pass/fail, strict overall pass,
  latency, and the final answer text. `correct` means routing only;
  `overall_pass` additionally requires exact tool selection and observable tool
  order. Regenerate by re-running the script above.
- `results_baseline_metadata.json` records the model, dataset partition, run
  date, and fixture coverage for the latest baseline.
- `results_pre_step4.csv` preserves the baseline used for the prompt experiment;
  `results_step4.csv` contains the post-change run used for the Step 4 delta.
- `../tools/build_eval_tracker.py` - builds `eval_tracker.xlsx` from
  `cases.json`, and from `results_baseline.csv` when present (falls back to
  informal spot-check notes otherwise). Re-run after either input changes:

  ```bash
  python tools/build_eval_tracker.py
  ```

The reviewed evaluation suite now has 30 cases, meeting the 30-50 golden
dataset size requirement. The 20-case `core_golden` set matches the required
mix exactly: 10 happy-path (50%), 6 edge (30%), 3 known-failure (15%), and 1
adversarial (5%). Ten cases live in `extended_regression`, run separately and
excluded from the core scenario-mix calculation: the original six, plus four
added to reach 30 total (`reassign-parent-only`, `cross-family-delete-not-
found`, `list-events-empty-family`, `draft-single-parent-reminder`) - all
reusing existing fixture strategies, each individually verified live (2/2
clean runs) before being added. All 30 cases now have deterministic fixture
strategies. The extended `provider-rate-limit` case still needs fault
injection. An executed `.ipynb` matching the reference deliverable format is
also outstanding-`run_baseline_eval.py` is currently a plain script, not a
notebook.
