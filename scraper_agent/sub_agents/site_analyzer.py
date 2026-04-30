"""
Site Analyzer Agent
Fetches the target URL and reports back on its structure:
- Is it static HTML or JavaScript-rendered?
- Does it expose a JSON API?
- Is there pagination, infinite scroll, anti-bot protection?
"""
from google.adk.agents import LlmAgent

from ..tools.fetch_tools import (
    fetch_static_html,
    fetch_with_browser,
    detect_json_apis,
    check_robots_txt,
)


site_analyzer_agent = LlmAgent(
    name="site_analyzer",
    model="gemini-2.0-flash",
    description="Analyzes a target website to understand its structure and rendering type.",
    instruction="""You analyze a target website so a downstream agent can scrape it.

Your input is in session state under keys `target_url` and `scrape_description`.

STEPS:
  1. Call `check_robots_txt(target_url)` and note any disallow rules.
  2. Call `fetch_static_html(target_url)`. Look at the returned HTML:
     - If the body is empty, tiny, or contains mostly <script> tags with
       little real content, the page is JavaScript-rendered.
     - If the body already contains the data the user asked for, it's static.
  3. If JS-rendered, call `fetch_with_browser(target_url)` to get the
     fully-rendered DOM.
  4. Call `detect_json_apis(target_url)` to find XHR/fetch endpoints the
     page calls in the background — these are often the easiest scrape target.
  5. Look for pagination patterns: `?page=`, `?offset=`, "Load more" buttons,
     infinite scroll, cursor-based APIs.
  6. Note any obvious anti-bot signals: Cloudflare, hCaptcha, rate-limit headers.

OUTPUT (write to session state under key `site_analysis` as a JSON object):
{
  "url": "...",
  "rendering": "static" | "javascript" | "hybrid",
  "recommended_approach": "requests+bs4" | "playwright" | "api",
  "discovered_apis": [{"url": "...", "method": "GET", "params": {...}}],
  "pagination": {"type": "page_param"|"cursor"|"scroll"|"none", "details": "..."},
  "anti_bot": ["cloudflare", "captcha", ...],
  "robots_allowed": true|false,
  "notes": "free-text observations for the next agent"
}

Be conservative — when in doubt, recommend `playwright` since it works on
both static and dynamic sites.
""",
    tools=[
        fetch_static_html,
        fetch_with_browser,
        detect_json_apis,
        check_robots_txt,
    ],
    output_key="site_analysis",
)
