# Failure Analysis — Week 4 Evaluation (2026-09-05)

Backing detail (per-row annotations, before/after deltas, regression checks)
lives in `week4_eval_tracker_Anusha.xlsx`, Steps 1-4 (dated 2026-09-05
sections). This is the condensed version: category names, grouped examples,
and the single most impactful failure type to address next.

Baseline: 30-case golden dataset, 25 distinct cases run live (33 runs incl.
repeats), strict pass 17/33 (52%), routing pass 20/33 (61%).

## Categories (grouped from every failing row, read individually before naming these)

| Category | Cases | Status |
|---|---|---|
| **Retry after rejection** | `approval-rejected` | Fixed |
| **Skipped required verification tool call** | `vikram-availability-rule`, `update-event-success` | Fixed |
| **Overclaiming in final-answer wording** | `draft-both-parent-reminder` | Fixed |
| **Filesystem fallback on empty search** | `cross-family-delete-not-found` | Fixed |
| **Rule over-generalization / regression** | `restore-event`, `create-future-event-with-location` (fixed), `reassign-parent-only` (open) | 2/3 fixed |
| **Premature mutation proposal** | `reject-past-event`, `school-event-overlap` | **Not addressed — see below** |
| **Non-termination / partial completion** | `weekly-deep-planning`, `hero-weekly-candidates` (both `known_failure` by design) | Not addressed this session |
| **Provider/model latency instability** | `same-child-conflict`, `vikram-availability-rule` (residual), `stale-weekly-option` | Accepted trade-off, not a code defect |
| **Under-specified activity reference** (same root cause as "under-specified relative time," on a sibling case) | `same-parent-conflict` | Partially fixed 2026-09-06 - improved but not reliable across repeated runs (see `step1-4_summary.xlsx`, Fix 7) |
| **Not yet triaged** | `family-outing-weekend` | Not investigated |

## Most impactful failure type to address next: Premature mutation proposal

**Definition:** the fast-path coordinator calls a mutation tool (`create_event`,
etc.) for a request that should be recognized as invalid *before* attempting
any tool call — relying on the repository's own guard (e.g.
`require_future_start`) to catch it via a rejected approval, instead of
refusing up front.

**Examples:**
- `reject-past-event`: calls `check_conflicts` and `create_event` for a
  provably-past event; only the DB-level guard (surfaced through a rejected
  approval) actually stops it.
- `school-event-overlap`: attempts the conflicting event before fully
  resolving the family- and school-calendar conflicts.

**Why this one, over the others:**
- It's a *known_failure* scenario type that has reproduced identically since
  the original 2026-09-02/03 baseline — it is not new, not fixed by any of
  today's six changes, and has now been observed on two different fast-path
  cases (not just one).
- It's a live safety-adjacent issue, not just a routing miss: it asks a human
  to approve a mutation that is guaranteed to fail, which wastes an approval
  cycle and risks eroding what the approval gate is supposed to mean if it
  keeps surfacing unapprovable requests.
- Unlike the deep-workflow non-termination cases (also `known_failure`, but
  already characterized as a delegated-chain-completion problem with a
  different, larger fix shape) and the provider-latency cluster (an accepted,
  already-evaluated trade-off — see the model-comparison section of
  `WEEK4_HANDOVER_2026-09-04.md`), this cluster is a bounded, prompt-level fix
  with a clear before/after signal already available (2 reproducing cases,
  identical shape both times).

**Recommended next fix (not yet implemented, flagged for a future session):**
add an explicit coordinator rule that a fast-path request must be validated
against known-invalid conditions (past start time, unresolved conflicting
event) *before* calling any mutation tool, not after — mirroring the
"resolve first, then act" pattern used successfully today for
`same-child-conflict` and `vikram-availability-rule`.

## What was NOT chased further, and why

- **`same-parent-conflict`, `family-outing-weekend`**: routing is correct but
  tool-selection/order and artifact-timing issues weren't triaged this
  session — time went to the six fixes above and the dataset expansion to 30
  cases instead.
- **Deep-workflow non-termination** (`weekly-deep-planning`,
  `hero-weekly-candidates`): unchanged 0/6 across the whole session; this is
  a larger, separate investigation (delegated multi-agent chain completion),
  not a quick prompt tweak.
- **Provider/model latency instability**: investigated directly — compared 3
  alternative models (`Qwen3-30B-A3B-Instruct-2507`, `Nemotron-3.5-Lightning`,
  `Llama-3.3-70B-Instruct`), all faster but each showed real safety
  violations (missed approval gates, mutations without conflict checks,
  attempted mutations on requests that should be rejected). Kept the current
  model and raised its provider request timeout (30s -> 60s) instead of
  chasing a swap. Full comparison data in `WEEK4_HANDOVER_2026-09-04.md`.
