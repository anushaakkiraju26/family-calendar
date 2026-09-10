# Short Walkthrough Script

~3-4 minutes. Four sections, no filler.

---

## What changed

> I ran my Week 3 agent against a 30-case golden dataset, read every failing
> run individually, and made six targeted fixes: stopping the agent from
> retrying a mutation after the parent rejected it, resolving an ambiguous
> time or activity reference from the calendar instead of asking the parent
> to restate it, correcting a reminder confirmation that implied delivery
> the app never performs, requiring a real availability check instead of
> trusting memorized policy text, and stopping the agent from falling back
> to filesystem search when a calendar lookup came back empty. I also
> expanded the dataset from 26 to 30 cases to meet the requirement.
>
> Separately, I found that the model configured as the project's actual
> default wasn't available at all anymore — a genuine 404, confirmed
> directly against the provider's model catalog, which meant the real
> product was broken by default, independent of anything the evaluation was
> testing. 


Before just swapping it to the next assigned default, I compared three faster alternative
> models against the same golden cases, and all three showed real safety
> violations — skipping the approval gate entirely, mutating without
> checking conflicts, attempting a mutation on a request that should be
> rejected outright — despite being faster. I kept the assigned default model, fixed
> the dead default, and raised its request timeout instead, since a
> slow-but-safe model beats a fast-but-unsafe one.

nvidia/Nemotron-3-Nano-Omni — the model that was configured as the project's default in .env but turned out to be genuinely unavailable (a real 404, confirmed directly against Nebius's model catalog, not a transient error). It was replaced with nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B, the closest available successor and the one that ultimately won the 3-way comparison against the alternatives.

Current model (kept): nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B — confirmed in .env as the committed default.

The 3 alternatives compared, all rejected:

nvidia/Nemotron-3.5-Lightning — fast, but mutated before checking conflicts, attempted a mutation instead of rejecting a conflict, and retried a mutation after rejection
Qwen/Qwen3-30B-A3B-Instruct-2507 — looked great on a small sample, but a broader 17-case run showed it missing the approval gate entirely, attempting mutations on cases that should be rejected, and silently correcting a stale plan version instead of flagging it
meta-llama/Llama-3.3-70B-Instruct — mutated with zero conflict check and a mangled event title, attempted a mutation on a conflict case, and missed the approval gate
All three were faster than the current model but showed real safety violations, which is why the current one was kept despite its latency variance.




## What improved

> Strict pass rate went from 9 out of 24 to 17 out of 33 across the session.
> Every fix has a specific before-and-after LangSmith trace showing the
> exact behavior change. The most important thing I can point to isn't a
> single fix, though — it's that one of my own fixes caused a regression on
> two previously-passing cases, and I caught it because I re-ran the full
> baseline after every change, not just the case I was targeting. I scoped
> the fix more precisely and re-verified all three cases together before
> moving on.
>
> On cost and latency: total token usage across the matched cases went up
> about 58%. At first that looks like a regression, but it isn't — several
> cases recorded close to zero tokens *before* because they timed out
> before doing any real work, so a low number there meant "failed
> immediately," not "was cheap." Latency actually went down about 10%
> overall, because fewer cases now ride out a full 60-or-240-second timeout
> with nothing to show for it — one case alone dropped from always timing
> out at 60 seconds to completing correctly in about 24.

## What still fails

> Four things, honestly reported rather than hidden in an aggregate number.
> One: the agent still attempts a mutation for a request that should be
> rejected outright, like a past-dated event, before checking whether it's
> even valid — reproduced on two separate cases, not yet fixed. Two: the
> deep weekly-planning workflow still doesn't complete within its time
> budget on either of its two test cases. Three: several cases show real
> latency variance in the underlying model — the identical prompt and
> fixture sometimes passes and sometimes times out. Four: one fix I tried
> today only partially worked — it improved the behavior but the case still
> shows inconsistent results across runs, including one where the agent
> delegates when it shouldn't.

## What I'd try next

> Fix the premature-mutation cluster first — it's the most bounded,
> best-understood remaining gap. Then dig into why the deep weekly workflow
> can't finish in time; that's a bigger investigation into the delegated
> multi-agent chain, not a one-line prompt change. And I'd get fixtures onto
> the five dataset cases that still don't have one, so the full 30 cases are
> actually exercised, not just described.
