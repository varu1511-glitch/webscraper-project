"""
Tool that renders the right scraper template into a standalone .py file.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined


TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
OUTPUT_DIR = Path(os.environ.get("SCRAPER_OUTPUT_DIR", "./generated_scrapers"))


_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


def _slugify(s: str) -> str:
    s = re.sub(r"https?://", "", s)
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()
    return s[:50] or "site"


def render_scraper_script(
    target_url: str,
    scrape_description: str,
    site_analysis: dict[str, Any],
    strategy: dict[str, Any],
    selectors: dict[str, Any],
) -> dict[str, Any]:
    """Render a standalone scraper script and write it to disk.

    Picks a template based on `strategy["approach"]`:
        api          -> api_scraper.py.j2
        static_html  -> static_scraper.py.j2
        browser      -> browser_scraper.py.j2
        hybrid       -> hybrid_scraper.py.j2

    Args:
        target_url: Target URL.
        scrape_description: User's natural-language description.
        site_analysis: Output of site_analyzer.
        strategy: Output of strategy_planner.
        selectors: Output of selector_extractor.

    Returns:
        dict with keys: script_path, template_used, pip_install_command,
        run_command, summary.
    """
    approach = strategy.get("approach", "static_html")
    template_map = {
        "api": "api_scraper.py.j2",
        "static_html": "static_scraper.py.j2",
        "browser": "browser_scraper.py.j2",
        "hybrid": "browser_scraper.py.j2",  # hybrid uses browser template
    }
    template_name = template_map.get(approach, "static_scraper.py.j2")
    template = _jinja_env.get_template(template_name)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"scraper_{_slugify(target_url)}_{timestamp}.py"
    script_path = (OUTPUT_DIR / filename).resolve()

    rendered = template.render(
        target_url=target_url,
        scrape_description=scrape_description,
        site_analysis=site_analysis,
        strategy=strategy,
        selectors=selectors,
        # JSON-encoded strings — embedded as raw string literals in the script
        # and parsed back via json.loads() at runtime. This avoids the
        # true/false/null mismatch between JSON and Python literals.
        selectors_json=json.dumps(selectors, indent=2),
        strategy_json=json.dumps(strategy, indent=2),
        generated_at=datetime.now().isoformat(timespec="seconds"),
    )

    script_path.write_text(rendered, encoding="utf-8")
    script_path.chmod(0o755)

    pip_packages = {
        "api": "requests",
        "static_html": "requests beautifulsoup4 lxml",
        "browser": "playwright",
        "hybrid": "playwright requests",
    }[approach]

    output_format = strategy.get("output_format", "csv")
    output_file = f"output.{output_format}"

    return {
        "script_path": str(script_path),
        "template_used": template_name,
        "pip_install_command": (
            f"pip install {pip_packages}"
            + (" && playwright install chromium" if "playwright" in pip_packages else "")
        ),
        "run_command": f"python {script_path.name} --output {output_file}",
        "summary": (
            f"Generated a {approach}-based scraper at {script_path}. "
            f"It uses the '{template_name}' template, paginates via "
            f"'{strategy.get('pagination_strategy', 'none')}', and writes "
            f"output as {output_format}."
        ),
    }
