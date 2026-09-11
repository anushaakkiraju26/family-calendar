# Week 5: Fine-Tune a Family Request Router

Custom-dataset variant of The Gen Academy's [Fine-Tune a Support Ticket Router](https://github.com/The-Gen-Academy/5A-Fine-Tune-a-Support-Ticket-Router)
project. Same recipe — `Qwen/Qwen3-1.7B-Base` + LoRA via LLaMA-Factory's LLaMA Board — applied
to this project's own data instead of IT tickets.

## What it does

Classifies a parent's request (e.g. *"Add Leo's soccer practice tomorrow from 4 to 5 PM for
family-1"*) into one of the six `target_workflow_category` labels the Family Coordinator
already uses internally to decide how to handle a request: `fast_path_mutate`,
`fast_path_read`, `fast_path_reject`, `deep_weekly_workflow`, `outing_workflow`,
`ambiguous_clarify`.

## Files

| File | What it is |
|---|---|
| `finetune_family_request_router.ipynb` | The Colab notebook — install, prepare data, train via LLaMA Board, merge, evaluate. Open it directly in Colab. |
| `../tools/generate_family_routing_dataset.py` | Builds the dataset: 30 real, eval-labelled requests (`evaluations/cases.json` + `evaluations/results_baseline.csv`) expanded with LLM-generated variations (same Nebius client the agent uses) to ~50 balanced examples per label. |
| `../data/family_request_routing.csv` | Full generated dataset (`text`, `category_truth`, `source`). |
| `../data/family_request_routing_train.csv` / `_val.csv` | Stratified 80/20 split, `text`/`category_truth` only — matches the reference project's CSV shape. |
| `../data/family_request_routing_manifest.json` | Label definitions and generation provenance/counts. |

Regenerate the dataset (needs `NEBIUS_API_KEY` in `.env`):

```
python tools/generate_family_routing_dataset.py --per-class 50
```

## Running the notebook

1. Open `finetune_family_request_router.ipynb` in Google Colab (free T4 runtime).
2. Run top to bottom. The dataset-prep cell clones this repo directly, so no manual CSV
   upload is needed as long as it's pushed to GitHub.
3. Everything else — LLaMA Board training, adapter merge, baseline comparison, evaluation —
   follows the reference project's flow; see the notebook's own cells for details.

## Submission

Per the Week 5 handout: using a custom dataset means submitting a GitHub link with all assets
plus a short Loom video, instead of the Google Doc + screenshot route.
