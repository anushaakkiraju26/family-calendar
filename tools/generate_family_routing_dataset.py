"""Generate a labelled dataset for the Week 5 fine-tuning project.

Task: given one parent request (short natural-language text), predict the
`target_workflow_category` the Family Coordinator should route it to. This is
the same shape as the reference project's ticket router (text -> one of N
labels), applied to this repo's own domain instead of IT support tickets.

Sources:
  - Real seed examples: evaluations/cases.json (prompt text) joined with
    evaluations/results_baseline.csv (target_workflow_category), 30 rows,
    all six labels represented.
  - Synthetic expansion: the Nebius-hosted chat model already configured for
    this project (same client family_activity_agent.agent uses) generates
    additional realistic, varied examples per label, few-shot prompted with
    the real seeds.

Output:
  - data/family_request_routing.csv       (text, category_truth) — all rows
  - data/family_request_routing_train.csv (80%, stratified)
  - data/family_request_routing_val.csv   (20%, stratified)
  - data/family_request_routing_manifest.json (counts + provenance)

Run:
  python tools/generate_family_routing_dataset.py --per-class 50
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent
CASES_PATH = REPO_ROOT / "evaluations" / "cases.json"
BASELINE_RESULTS_PATH = REPO_ROOT / "evaluations" / "results_baseline.csv"
DATA_DIR = REPO_ROOT / "data"

LABELS: dict[str, str] = {
    "fast_path_mutate": (
        "A single, specific calendar or reminder mutation the coordinator can "
        "execute directly after conflict checks: create, update, move, delete, "
        "or restore an event, or draft/cancel a reminder, for one clear family "
        "and activity. Pending parent approval before the mutating tool call."
    ),
    "fast_path_read": (
        "A single, specific read-only request: list or show existing events, "
        "reminders, or activities for a family, child, or date range. No "
        "mutation, no approval gate."
    ),
    "fast_path_reject": (
        "A single, specific request that must be declined outright by "
        "deterministic safeguards: a past-dated event, a direct child/parent/"
        "transportation conflict, cross-family access, a stale plan version, "
        "or an unsafe retry after a prior rejection."
    ),
    "deep_weekly_workflow": (
        "A broad, multi-day coordination request needing the full specialist "
        "pipeline (intake, weekly planner, transportation, schedule reviewer, "
        "reminder agent) to check school and family calendars, resolve "
        "conflicts, and produce a reviewed weekly plan."
    ),
    "outing_workflow": (
        "A request for cited outing or activity ideas for a weekend or school "
        "break, routed to the Family Outing Agent's constrained search wrapper. "
        "Never mutates the calendar."
    ),
    "ambiguous_clarify": (
        "A request missing information the coordinator needs before acting "
        "(which event, which family, which time) and must be answered with a "
        "clarifying question rather than a tool call."
    ),
}

CHILD_NAMES = ["Leo", "Maya", "Ava", "Noah", "Priya", "Zoe", "Ben", "Sofia", "Kai", "Ruby"]
FAMILY_IDS = ["family-1", "family-2", "family-3", "family-4"]
ACTIVITIES = [
    "soccer practice", "piano lesson", "dentist appointment", "swim class",
    "tutoring session", "birthday party", "art class", "playdate",
    "orthodontist visit", "gymnastics", "chess club", "school pickup",
]


def load_seed_examples() -> list[dict[str, str]]:
    cases = json.loads(CASES_PATH.read_text())
    prompt_by_id = {c["id"]: c["prompt"] for c in cases}

    category_by_id: dict[str, str] = {}
    with BASELINE_RESULTS_PATH.open() as f:
        for row in csv.DictReader(f):
            cid = row["case_id"]
            cat = row["target_workflow_category"]
            if cid not in category_by_id and cat:
                category_by_id[cid] = cat

    seeds = []
    for cid, prompt in prompt_by_id.items():
        cat = category_by_id.get(cid)
        if cat and cat in LABELS:
            seeds.append({"text": prompt, "category_truth": cat, "source": "seed"})
    return seeds


def build_client():
    from langchain_openai import ChatOpenAI

    api_key = os.getenv("NEBIUS_API_KEY")
    if not api_key:
        raise RuntimeError("Add NEBIUS_API_KEY to .env before generating data.")
    return ChatOpenAI(
        model=os.getenv("FAMILY_ACTIVITY_MODEL", "Qwen/Qwen3-30B-A3B-Instruct-2507"),
        api_key=api_key,
        base_url=os.getenv("NEBIUS_BASE_URL", "https://api.studio.nebius.com/v1/"),
        temperature=1.0,
    )


def extract_json_array(text: str) -> list[str]:
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON array found in model output: {text[:200]!r}")
    return json.loads(match.group(0))


def generate_batch(client, label: str, description: str, seed_texts: list[str], n: int) -> list[str]:
    entity_hint = (
        f"Vary child names across {CHILD_NAMES}, family ids across {FAMILY_IDS}, "
        f"and activities across {ACTIVITIES}. Vary phrasing register: some terse "
        "and text-message-like, some polite and fully written out, some with "
        "typos or mid-sentence corrections. Do not repeat any seed example "
        "verbatim."
    )
    prompt = (
        "You are generating training data for a text classifier that routes a "
        "parent's request to a family-calendar coordinator agent.\n\n"
        f"Label: {label}\n"
        f"Definition: {description}\n\n"
        "Real example requests that belong to this label:\n"
        + "\n".join(f"- {t}" for t in seed_texts)
        + f"\n\n{entity_hint}\n\n"
        f"Write {n} NEW, realistic parent request messages that all belong to "
        "this exact label. Each must be a short, standalone message a parent "
        "would actually type or say — not a description of the label, not a "
        "solution, no explanations. "
        'Return ONLY a JSON array of strings, e.g. ["...", "...", ...].'
    )
    response = client.invoke(prompt)
    return extract_json_array(response.content)


def stratified_split(rows: list[dict[str, str]], val_frac: float, seed: int):
    by_label: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_label[row["category_truth"]].append(row)

    rng = random.Random(seed)
    train, val = [], []
    for label, items in by_label.items():
        items = items[:]
        rng.shuffle(items)
        n_val = max(1, round(len(items) * val_frac))
        val.extend(items[:n_val])
        train.extend(items[n_val:])
    rng.shuffle(train)
    rng.shuffle(val)
    return train, val


def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] for k in columns})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-class", type=int, default=50, help="target rows per label")
    parser.add_argument("--batch-size", type=int, default=12, help="rows requested per LLM call")
    parser.add_argument("--val-frac", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args()

    seeds = load_seed_examples()
    seeds_by_label: dict[str, list[str]] = defaultdict(list)
    for row in seeds:
        seeds_by_label[row["category_truth"]].append(row["text"])

    print(f"Loaded {len(seeds)} real seed examples across {len(seeds_by_label)} labels.")

    client = build_client()
    all_rows: list[dict[str, str]] = list(seeds)
    seen_texts = {row["text"].strip().lower() for row in seeds}

    for label, description in LABELS.items():
        existing = [r for r in all_rows if r["category_truth"] == label]
        seed_texts = seeds_by_label.get(label, [])
        if not seed_texts:
            print(f"  ! no real seeds for {label}; using label description only")
            seed_texts = [description]

        attempts = 0
        while len([r for r in all_rows if r["category_truth"] == label]) < args.per_class and attempts < 20:
            attempts += 1
            need = args.per_class - len([r for r in all_rows if r["category_truth"] == label])
            batch_n = min(args.batch_size, max(need + 4, 4))  # ask for a few extra to survive dedup
            try:
                candidates = generate_batch(client, label, description, seed_texts, batch_n)
            except Exception as exc:  # noqa: BLE001
                print(f"  ! generation error for {label} (attempt {attempts}): {exc}")
                continue
            added = 0
            for text in candidates:
                text = str(text).strip()
                key = text.lower()
                if not text or key in seen_texts:
                    continue
                seen_texts.add(key)
                all_rows.append({"text": text, "category_truth": label, "source": "synthetic"})
                added += 1
            print(f"  {label}: +{added} (total {len([r for r in all_rows if r['category_truth'] == label])}/{args.per_class})")

    counts = defaultdict(int)
    for row in all_rows:
        counts[row["category_truth"]] += 1
    print("\nFinal counts:", dict(counts))

    DATA_DIR.mkdir(exist_ok=True)
    full_path = DATA_DIR / "family_request_routing.csv"
    train_path = DATA_DIR / "family_request_routing_train.csv"
    val_path = DATA_DIR / "family_request_routing_val.csv"
    manifest_path = DATA_DIR / "family_request_routing_manifest.json"

    write_csv(full_path, all_rows, ["text", "category_truth", "source"])

    train_rows, val_rows = stratified_split(all_rows, args.val_frac, args.seed)
    write_csv(train_path, train_rows, ["text", "category_truth"])
    write_csv(val_path, val_rows, ["text", "category_truth"])

    manifest = {
        "labels": LABELS,
        "counts_total": dict(counts),
        "train_count": len(train_rows),
        "val_count": len(val_rows),
        "real_seed_count": len(seeds),
        "synthetic_count": len(all_rows) - len(seeds),
        "generator_model": os.getenv("FAMILY_ACTIVITY_MODEL", "Qwen/Qwen3-30B-A3B-Instruct-2507"),
        "sources": {
            "seed_prompts": "evaluations/cases.json",
            "seed_labels": "evaluations/results_baseline.csv (target_workflow_category)",
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))

    print(f"\nWrote {len(all_rows)} rows -> {full_path}")
    print(f"Wrote {len(train_rows)} train rows -> {train_path}")
    print(f"Wrote {len(val_rows)} val rows -> {val_path}")
    print(f"Manifest -> {manifest_path}")


if __name__ == "__main__":
    main()
