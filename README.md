# Urban Nest Estates — Instagram Content Agent (V2, local prototype)

Generates a plan of 3 varied Instagram posts per week from local mock data,
using local history so weeks don't repeat themselves. No external
integrations (no Google Drive, Instagram API, n8n, GitHub Actions, scheduling,
or auto-publishing).

## Run it

```bash
pip install -r requirements.txt
python3 main.py
python3 main.py --week-of 2026-09-08   # override the week label (useful for demos/tests)
```

Runs fully offline by default. To use Claude for planning + copywriting,
copy `.env.example` to `.env`, set `ANTHROPIC_API_KEY`, and `export` it (or
load it) before running — the API key is never read from source, only from
the environment, and `.env` is gitignored.

Run the test suite with:

```bash
python3 -m unittest discover -s tests -t .
```

## Files

- `mock_data.py` — fake property records, brand/context info, and the
  content-type catalogue (each type tagged with a soft content-mix `bucket`).
  Edit this to change what the agent knows.
- `history.py` — reads previously saved weekly plans from `output/` and
  summarizes what was used recently (content types, properties, formats,
  hooks), plus the freshness-ranking helpers used to favor variety.
- `planner.py` — decides WHAT to post about this week (3 posts: content type
  + property, if any), using the history summary to disfavor recent repeats.
  Guarantees all 3 types are distinct and at most one is a property showcase.
  Uses Claude when `ANTHROPIC_API_KEY` is set; its output is validated and
  backfilled from the offline heuristic if invalid.
- `generator.py` — turns a decided post into full copy: objective, content
  idea, hook, visual needed, caption, CTA, and a history-aware format choice.
- `main.py` — orchestrates the above, prints the plan (including each post's
  `reason`), saves it as JSON to `output/weekly_plan_<date>.json`.
- `tests/` — unit tests for the history/freshness logic, the offline planner
  fallback, and the generator, run with no API key required.

## Key architectural decisions

- **Variety is enforced in code, not left to chance.** The planner always
  picks 3 distinct content types and caps property showcases at one per
  week, so the "don't make it all property showcases" requirement can't
  silently fail.
- **History reuses the existing saved output — no new storage layer.** V2's
  "content history" is just `history.py` reading back the `weekly_plan_*.json`
  files `main.py` already writes each run. No database, no extra file format.
- **Diversity is a bias, not a hard ban.** Recently-used content types,
  properties, and formats get a lower (but never zero) selection weight, so
  repeats are still possible when nothing fresher fits — matching "diversity
  by default, repeats allowed for a good reason."
- **Claude proposes, code disposes.** When Claude makes the weekly call, its
  picks are validated against the hard constraints (distinct types, ≤1
  showcase, valid property ids) and any invalid pick is dropped and
  backfilled by the same offline heuristic — so a malformed model response
  can't break a run.
- **No invented property facts.** When a post is about a specific property,
  the generator passes only that property's own record from `mock_data.py`
  into the prompt and explicitly instructs the model not to add details
  beyond it. Non-property posts are told not to reference any property,
  price, or review as fact.
- **Works with zero setup.** If no `ANTHROPIC_API_KEY` is present (or the
  API call fails for any reason), the agent falls back to deterministic,
  history-aware rules instead of crashing, so the pipeline is always
  testable end-to-end locally.
- **Mock data lives in plain Python, not JSON/a database.** For a handful of
  records, a Python file is the simplest thing that works and is trivial to
  edit by hand.
