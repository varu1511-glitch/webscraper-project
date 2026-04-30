"""
Strategy Planner Agent
Reads the site analysis and decides the exact scraping strategy.
"""
from google.adk.agents import LlmAgent


strategy_planner_agent = LlmAgent(
    name="strategy_planner",
    model="gemini-2.0-flash",
    description="Picks the optimal scraping strategy based on site analysis.",
    instruction="""You are a scraping strategy planner.

Read `site_analysis` and `scrape_description` from session state.

Decide the BEST strategy. Pick exactly one of:
  - "api"        : Site exposes a JSON endpoint that returns the data directly.
                   Fastest and most reliable. Use whenever possible.
  - "static_html": Server returns full HTML. Use requests + BeautifulSoup.
  - "browser"    : JS-rendered, no API found. Use Playwright.
  - "hybrid"     : Use Playwright to load the page, then intercept its API calls.

Also decide:
  - pagination_strategy: how to get all pages (page param, cursor, scroll, none)
  - rate_limit_seconds: float, polite delay between requests (default 1.0,
                        increase to 2-3 for sites with anti-bot)
  - needs_user_agent: whether to send a realistic User-Agent header (almost always yes)
  - needs_session: whether to maintain cookies across requests
  - output_format: csv | json | jsonl  (pick based on what user asked for;
                   default to csv for tabular data, json for nested data)

OUTPUT to session state key `strategy` as JSON:
{
  "approach": "api" | "static_html" | "browser" | "hybrid",
  "reasoning": "1-2 sentences why",
  "pagination_strategy": "...",
  "rate_limit_seconds": 1.0,
  "needs_user_agent": true,
  "needs_session": false,
  "output_format": "csv",
  "target_endpoints_or_pages": ["url1", "url2", ...]
}
""",
    output_key="strategy",
)
