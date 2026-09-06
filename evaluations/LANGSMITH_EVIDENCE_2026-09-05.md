# LangSmith Evidence — Week 4 Evaluation (2026-09-05, extended 2026-09-06)

All links below are **public LangSmith share links** (via `client.share_run`)
— viewable by anyone with the URL, no LangSmith account or workspace access
required. Every eval run this session was traced under one project:

**Project (requires workspace access — use the public run links below instead
for anyone outside this workspace):**
`family-activity-agent-week4-eval`

Every row of every `results_*.csv` in `evaluations/` carries the exact
`langsmith_run_id` for its run, so any case/run pair not listed below can
still be looked up and shared the same way
(`Client().share_run(run_id)` or `client.read_run_shared_link(run_id)` if
already shared).

## Baseline run (full picture)

- **Original baseline** (9/24 strict pass): `evaluations/results_baseline_2026-09-04-pre-triage.csv`
- **Final baseline** (17/33 strict pass, 30-case dataset): `evaluations/results_baseline.csv`
- Full run-by-run trajectory and reasoning: `evaluations/WEEK4_HANDOVER_2026-09-04.md`
- Condensed failure analysis: `evaluations/FAILURE_ANALYSIS_2026-09-05.md`

## Per-fix before/after traces (matches Step 4 of `week4_eval_tracker_Anusha.xlsx`)

### Fix A — Retry after rejection (`approval-rejected`)
- BEFORE (retries `update_event` after rejection, times out): https://smith.langchain.com/public/eeff12c8-ff60-4d21-9a2e-0248abcc90ab/r
- AFTER (stops after rejection, acknowledges it): https://smith.langchain.com/public/00ea2bad-afc0-4afa-8f37-dc31e08e2643/r

### Fix B — Under-specified relative time (`same-child-conflict`)
- BEFORE (times out, 0 tool calls): https://smith.langchain.com/public/a210d48a-9328-4659-a004-5ca0efd1aadd/r
- AFTER, from the final 30-case baseline (still shows residual latency variance — this run timed out again; see the Fix B note in the spreadsheet for the separate 2/2 and clean single-run verification batches that confirm the logic itself is correct): https://smith.langchain.com/public/bbd3b68b-fa4f-403a-9725-6e58502a74ca/r

### Fix D — Skipped required verification tool call (`vikram-availability-rule`, `update-event-success`)
- `vikram-availability-rule` BEFORE (0 tool calls, memorized-rule answer): https://smith.langchain.com/public/b74cd6dc-6802-4343-8172-ffab322d8327/r
- `vikram-availability-rule` AFTER, from the final 30-case baseline (this specific run timed out — again, residual model latency; see the spreadsheet's Fix D note for the 2/2 and 3/3 clean verification batches on separate days): https://smith.langchain.com/public/fb6a867a-aa63-4327-a68b-45ba0ce19dd9/r
- `update-event-success` BEFORE (skips `check_conflicts`, times out): https://smith.langchain.com/public/0514a5ea-7952-4851-b7e2-740070535c06/r
- `update-event-success` AFTER (clean, all 3 repeat runs passed): https://smith.langchain.com/public/4a157f46-0a27-439b-9bef-b49c618d6631/r

### Fix E — Rule over-generalization / regression (`restore-event`, `create-future-event-with-location`)
- `restore-event` REGRESSED (Fix D's rule bled into `restore_event`, extra `check_conflicts` call): https://smith.langchain.com/public/6fbe03f9-f15e-45a7-8dca-3e69c127502a/r
- `restore-event` FIXED (scoped rule, clean again): https://smith.langchain.com/public/fdcbc804-2137-477f-a73d-a4d662b3a0d2/r
- `create-future-event-with-location` REGRESSED (duplicate `check_conflicts` call): https://smith.langchain.com/public/a3135507-95b2-4ed6-a9fc-54e1a499c8ac/r
- `create-future-event-with-location` FIXED: https://smith.langchain.com/public/85269be9-e1f8-41d4-960d-27a80f02fb0e/r

### Fix F — Filesystem fallback on empty search (`cross-family-delete-not-found`)
- FIXED (this is a newly-added case; the pre-fix failing runs that called `ls`/`glob`/`grep` were only saved to the overwritten `results_diagnostic.csv` and their run IDs weren't retained — the failure is documented qualitatively in the spreadsheet and handover instead): https://smith.langchain.com/public/120fcf85-e7cb-401f-b20d-f64b208d29ed/r

### New dataset cases (added to reach the 30-case requirement)
- `list-events-empty-family`: https://smith.langchain.com/public/2c3ce4d3-9795-4b9e-860f-05554bad8fb9/r
- `draft-single-parent-reminder` (fixed — first draft used a past reminder time): https://smith.langchain.com/public/9aeb78c0-e4fe-4c05-9be1-5f5e981dc108/r
- `reassign-parent-only` (**open issue, not yet fixed** — over-calls `check_parent_availability`/`check_conflicts`): https://smith.langchain.com/public/570f8e9c-ccf3-4f84-90c8-99bba1a767c7/r

### Fix 7 (2026-09-06) — Under-specified activity reference (`same-parent-conflict`)
- BEFORE (0 tool calls, asks the parent to restate both activities' details immediately): https://smith.langchain.com/public/91dfd07a-940a-46cf-943f-c3a1cde23444/r
- AFTER (**partial — not a clean fix**: this run erroneously delegates via `task` instead of staying fast-path, then asks anyway; other verification runs called `list_events` and reasoned about the conflict manually without `check_conflicts`, or hit a runtime error/timeout. Documented honestly as open in `step1-4_summary.xlsx`, Step 4 Fix 7 and `FAILURE_ANALYSIS_2026-09-05.md`): https://smith.langchain.com/public/658b8157-9bf3-4cee-912f-c92b55b8924d/r

## Note on sharing

`share_run` publishes the individual trace publicly on the internet (no
login required to view). The content is synthetic test data only — fake
family/child names, fake calendar events, no real personal information — so
this carries no privacy risk, but flagging it since it is an outward-facing,
technically-permanent action (LangSmith does allow revoking a share via
`client.unshare_run(run_id)` if you ever want to pull one down).
