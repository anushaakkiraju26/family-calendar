# Short Walkthrough Script

~2-3 minutes. Four sections, no filler.

---

## What changed

> I ran my Week 3 agent against a 30-case golden dataset, read every failing
> run individually, and made six targeted fixes: stopping the agent from
> retrying a mutation after the parent rejected it, resolving an ambiguous
> time or activity reference from the calendar instead of asking the parent
> to restate it, correcting a reminder confirmation that implied delivery
> the app never performs, requiring a real availability check instead of
> trusting memorized policy text, and stopping the agent from falling back
> to filesystem search when a calendar lookup came back empty. I also raised
> the provider request timeout, expanded the dataset from 26 to 30 cases to
> meet the requirement, and compared three faster alternative models before
> deciding to keep the current one.

## What improved

> Strict pass rate went from 9 out of 24 to 17 out of 33 across the session.
> Every fix has a specific before-and-after LangSmith trace showing the
> exact behavior change. The most important thing I can point to isn't a
> single fix, though — it's that one of my own fixes caused a regression on
> two previously-passing cases, and I caught it because I re-ran the full
> baseline after every change, not just the case I was targeting. I scoped
> the fix more precisely and re-verified all three cases together before
> moving on.

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
