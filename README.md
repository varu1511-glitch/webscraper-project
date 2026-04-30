# Google ADK Web Scraping Agent

A multi-agent system built on Google's Agent Development Kit that takes a
URL + a description of what to scrape and produces a **standalone Python
scraper script**. The generated script runs without the agent — just
`python scraper.py`.

## Architecture

```
                  ┌─────────────────────────────────┐
User ──URL+desc──▶│  web_scraping_orchestrator      │
                  │         (root_agent)            │
                  └──────────────┬──────────────────┘
                                 │ delegates to
                                 ▼
                  ┌─────────────────────────────────┐
                  │       scraping_pipeline          │
                  │       (SequentialAgent)         │
                  └──────────────┬──────────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        ▼                        ▼                        ▼
  site_analyzer  ──▶  strategy_planner  ──▶  selector_extractor
                                                           │
                                ┌──────────────────────────┘
                                ▼
                       code_generator  ──▶  validator
                                                │
                                                ▼
                              standalone_scraper.py  📄
```

Each sub-agent does one thing well:

| Agent              | Role                                                         |
|--------------------|--------------------------------------------------------------|
| `site_analyzer`    | Fetches the page (static + headless), checks robots.txt, detects SPAs and background JSON APIs |
| `strategy_planner` | Picks `api` / `static_html` / `browser` / `hybrid`           |
| `selector_extractor` | Finds CSS selectors or JSON paths for each requested field |
| `code_generator`   | Renders the matching Jinja template into a `.py` file       |
| `validator`        | Runs the generated script with `--max-pages 1` and confirms it produced data |

## Why three templates?

- **`api_scraper.py.j2`** — when the page calls a JSON endpoint in the background, scraping the API directly is 10× faster and more reliable
- **`static_scraper.py.j2`** — for server-rendered HTML, plain `requests + bs4`
- **`browser_scraper.py.j2`** — for JS-heavy SPAs, uses Playwright

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env  # fill in GOOGLE_API_KEY
```

## Run

```bash
adk web              # launches the ADK web UI
# or
adk run scraper_agent
```

Then ask:

> Scrape https://books.toscrape.com — I want title, price, rating, and stock status of every book

The agent will produce something like `./generated_scrapers/scraper_books_toscrape_com_20260430_141522.py`. That file is **fully standalone** — copy it to any machine, `pip install requests beautifulsoup4 lxml`, and run.

## What makes the generated scripts robust

Every generated script includes:

- CLI flags: `--url`, `--output`, `--format`, `--max-pages`
- Realistic User-Agent
- Exponential-backoff retries (3 attempts)
- Configurable rate limiting between pages
- Pagination handling (link-based, page-param, or infinite-scroll)
- Output as CSV, JSON, or JSONL
- stderr logging so you can watch progress
- Exit codes for shell pipelines

## Scaling to many sites

The agent itself is generic — give it any URL and it adapts. To scrape a long list of sites in batch, use the agent once per site to generate scripts, then run all the generated scripts in parallel via your scheduler of choice (cron, Airflow, GitHub Actions, etc.). The scripts have no dependency on the agent at runtime.

## Project layout

```
scraper_agent/
├── agent.py                    # Root orchestrator
├── sub_agents/
│   ├── site_analyzer.py
│   ├── strategy_planner.py
│   ├── selector_extractor.py
│   ├── code_generator.py
│   └── validator.py
├── tools/
│   ├── fetch_tools.py          # static + browser fetching, robots.txt, API detection
│   ├── selector_tools.py       # DOM sampling, selector testing, JSON path extraction
│   ├── codegen_tools.py        # Jinja rendering
│   └── validator_tools.py      # subprocess test runs + output inspection
└── templates/
    ├── api_scraper.py.j2
    ├── static_scraper.py.j2
    └── browser_scraper.py.j2
```

## Legal note

Always check the target site's `robots.txt` and Terms of Service before scraping. The agent surfaces robots.txt status in its analysis, but the responsibility to scrape ethically and legally is yours.
