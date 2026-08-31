# Urban Nest Estates — Instagram Content Agent (V1, local prototype)

Generates a plan of 3 varied Instagram posts per week from local mock data.
No external integrations (no Google Drive, Instagram API, n8n, GitHub Actions).

## Run it

```bash
pip install -r requirements.txt
python3 main.py
```

Runs fully offline by default. To use Claude for the actual copywriting,
copy `.env.example` to `.env`, set `ANTHROPIC_API_KEY`, and `export` it (or
load it) before running — the API key is never read from source, only from
the environment, and `.env` is gitignored.

## Files

- `mock_data.py` — fake property records, brand/context info, and the
  content-type catalogue. Edit this to change what the agent knows.
- `planner.py` — picks 3 content types for the week and guarantees variety:
  all 3 types are distinct, and at most one is a property showcase.
- `generator.py` — turns a chosen content type (+ property, if relevant)
  into a full post: objective, content idea, hook, visual needed, caption,
  CTA, and format (Carousel / Reel concept / Story / Normal post). Uses
  Claude if `ANTHROPIC_API_KEY` is set, otherwise a template fallback.
- `main.py` — orchestrates the above, prints the plan, saves it as JSON to
  `output/weekly_plan_<date>.json`.

## Key architectural decisions

- **Variety is enforced in code, not left to chance.** The planner always
  picks 3 distinct content types and caps property showcases at one per
  week, so the "don't make it all property showcases" requirement can't
  silently fail.
- **No invented property facts.** When a post is about a specific property,
  the generator passes only that property's own record from `mock_data.py`
  into the prompt and explicitly instructs the model not to add details
  beyond it. Non-property posts are told not to reference any property,
  price, or review as fact.
- **Works with zero setup.** If no `ANTHROPIC_API_KEY` is present (or the
  API call fails for any reason), the agent falls back to deterministic
  templates instead of crashing, so the pipeline is always testable
  end-to-end locally.
- **Mock data lives in plain Python, not JSON/a database.** For a V1 with a
  handful of records, a Python file is the simplest thing that works and is
  trivial to edit by hand.
