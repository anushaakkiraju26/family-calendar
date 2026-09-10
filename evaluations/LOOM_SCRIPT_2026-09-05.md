# Loom Script — Week 4 Evaluation Walkthrough

Aim for ~7-9 minutes. Each section has a rough time budget and a `[SHOW: ...]`
cue for what to have on screen. Read it loosely, not word-for-word — the
cues matter more than the exact phrasing.

---

## 1. Intro (20s)

`[SHOW: your agent's repo / the family-activity-agent README]`

> This is my Week 4 evaluation of my own Week 3 project — the Family
> Activity Agent, a household-calendar assistant that coordinates events,
> conflicts, transportation, and reminders across a family. I evaluated it
> against a 30-case golden dataset with automated metrics and LangSmith
> tracing, found real failures, fixed six of them, and re-measured.

## 2. Evaluation setup (45s)

`[SHOW: evaluations/cases.json, or the Golden Dataset tab of week4_eval_tracker_Anusha.xlsx]`

> The golden dataset has 30 cases — 20 core cases split 50% happy path, 30%
> edge case, 15% known failure, 5% adversarial, plus 10 extended regression
> cases. 
>
> Every case checks three things automatically: did the agent route to the
> right workflow, did it call the exact expected tools, and did it call them
> in the right order. 

`[SHOW: the LangSmith project, or one shared run link from LANGSMITH_EVIDENCE_2026-09-05.md]`

> Every run is traced in LangSmith — one trace per case, with the
> case_id, target category, and outcome recorded as metadata, so I can go
> from an aggregate number straight down to the exact failing run.

## 3. Baseline (45s)

`[SHOW: week4_eval_tracker_Anusha.xlsx, Step 1 — Baseline+Failures]`

> The first full baseline run was 9 out of 24 strict passes — 37%. I read
> every single failing row before naming any categories, which is the
> workflow this course pushes, and it's the right call: some of what looked
> like the same bug were actually different root causes.

## 4. What changed — six fixes (2 minutes)

`[SHOW: week4_eval_tracker_Anusha.xlsx, Step 4 — Tweak the Prompt, the six 2026-09-05 fix blocks]`

> I made six targeted prompt and runner fixes today. I'll walk through the
> two most interesting ones, and one really important regression story.

**Fix A — retry after rejection:**
`[SHOW: LangSmith BEFORE/AFTER pair for approval-rejected]`

> When a parent rejected a calendar change, the agent kept retrying the
> same mutation instead of stopping — which is a real safety problem, since
> it undermines what the approval gate is supposed to mean. I added an
> explicit rule: stop immediately, acknowledge the rejection, don't retry.
> You can see the before run timing out after repeated retries, and the
> after run stopping cleanly and asking what to do next.

**Fix D/E — the regression story:**
`[SHOW: the restore-event and create-future-event-with-location REGRESSED/FIXED pairs]`

> This is the one I want to highlight. I fixed a case where the agent
> skipped a required conflict check — but my fix was worded too broadly, and
> it caused the agent to start over-calling that same check on two
> *previously-passing* cases. I only caught this because I re-ran the full
> baseline after every fix, not just the target case. I scoped the rule more
> precisely, re-verified all three affected cases together, and confirmed
> six-for-six clean. That's the regression-testing discipline this checklist
> asks for, and it's the single most important habit from this whole
> session.

> The other four fixes — resolving a relative time instead of asking the
> parent to restate it, requiring a real tool call instead of trusting
> memorized policy text, fixing overclaiming language in a reminder
> confirmation, and stopping the agent from falling back to filesystem
> search when a calendar lookup came back empty — are all documented with
> the same before/after evidence in the spreadsheet and in
> FAILURE_ANALYSIS_2026-09-05.md.

## 5. Measured impact — pass rate, cost, latency (1 minute)

`[SHOW: the strict-pass trajectory — 9/24 → 11/24 → 14/28 → 17/33]`

> Strict pass rate went from 9 out of 24 to 17 out of 33 across the session,
> as the dataset also grew to meet the 30-case requirement.

`[SHOW: step1-4_summary.xlsx, "Cost Comparison" tab]`

> Cost and latency moved in different directions, and both numbers need
> context, not just the raw delta. Total token usage across the matched
> cases went up about 58% — that looks bad at first glance, but several
> cases recorded close to zero tokens *before* only because they timed out
> before doing any real work. A low token count there meant "failed
> immediately," not "was cheap." Latency actually went down about 10%
> overall, because fewer cases now ride out a full 60-or-240-second timeout
> with nothing to show for it.

## 6. Model unavailability and model selection (1-1.5 minutes)

`[SHOW: the .env diff (FAMILY_ACTIVITY_MODEL), or the WEEK4_HANDOVER.md "Model comparison investigation" section]`

> Separate from the eval fixes, I found a real production bug: the model
> configured as this project's actual default, `nvidia/Nemotron-3-Nano-Omni`,
> wasn't available anymore — a genuine 404, confirmed directly against the
> provider's own model catalog. That meant the real app was broken by
> default, independent of anything the evaluation was testing.
>
> Before just swapping it for whatever was fastest, I compared three
> alternative models against the same golden cases:

`[SHOW: results_model_compare_*.csv files, or the model-comparison table in WEEK4_HANDOVER.md]`

> `Nemotron-3.5-Lightning` mutated before checking conflicts and retried a
> mutation after rejection. `Qwen3-30B-A3B-Instruct-2507` looked great on a
> small sample, but a broader run showed it missing the approval gate
> entirely. `Llama-3.3-70B-Instruct` mutated with zero conflict check at
> all. All three were faster than what I ended up keeping,
> `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, but every one of them showed a
> real safety violation the current model doesn't. I kept it, fixed the
> dead default in `.env`, and raised its request timeout instead — a
> slow-but-safe model beats a fast-but-unsafe one.

## 7. Remaining failures (45s)

`[SHOW: FAILURE_ANALYSIS_2026-09-05.md]`

> Three kinds of failures are still open. First, "premature mutation
> proposal" — the agent attempts a mutation for a request that should be
> rejected outright, like a past-dated event, instead of catching it before
> calling any tool. That's my top priority for next time — it's reproduced
> on two separate cases and it's a bounded, well-understood fix. Second, the
> two deep-weekly-planning cases still don't complete within budget — that's
> a bigger, separate investigation into the delegated multi-agent chain.
> Third, a handful of cases show real model-latency variance rather than
> logic bugs — the same fixture sometimes passes and sometimes times out,
> which I've documented rather than tried to paper over with a longer
> timeout.

## 8. Next steps (15s)

> Next: fix the premature-mutation-proposal cluster, get fixtures onto the
> five still-pending extended cases, and take a real pass at why the deep
> weekly workflow can't complete in time.

---

**Closing line:** "That's the full loop — baseline, failure analysis,
targeted fixes, regression checks, and a measured delta. Thanks for
watching."
