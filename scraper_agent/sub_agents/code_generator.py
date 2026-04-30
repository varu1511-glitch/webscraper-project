"""
Code Generator Agent
Renders one of the script templates with the strategy + selectors
into a runnable, standalone Python file.
"""
from google.adk.agents import LlmAgent

from ..tools.codegen_tools import render_scraper_script


code_generator_agent = LlmAgent(
    name="code_generator",
    model="gemini-2.0-flash",
    description="Generates a standalone Python scraper script.",
    instruction="""You generate a standalone Python script.

Read from session state:
  - `target_url`
  - `scrape_description`
  - `site_analysis`
  - `strategy`
  - `selectors`

Call `render_scraper_script` ONCE with all of those as arguments.
The tool picks the right Jinja template based on `strategy.approach`
(api / static_html / browser / hybrid) and writes the file to disk.

The generated script MUST:
  - Run with `python scraper.py` — no agent, no extra setup beyond pip install
  - Read its config (URL, output path) from CLI args, with sensible defaults
  - Handle pagination automatically until exhausted or a --max-pages flag
  - Respect a configurable rate limit between requests
  - Send a realistic User-Agent
  - Retry failed requests with exponential backoff (3 attempts)
  - Write output as CSV or JSON based on strategy.output_format
  - Log progress to stderr so users see what's happening
  - Include a top-of-file docstring listing required pip packages

After rendering, write the absolute path to session state under key
`generated_script_path` and a short human-readable summary under
`generation_summary`.
""",
    tools=[render_scraper_script],
    output_key="generation_summary",
)
