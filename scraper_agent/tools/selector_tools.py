"""
Tools for inspecting DOM structure and validating CSS selectors.
"""
from __future__ import annotations

import json
from typing import Any

import requests
from bs4 import BeautifulSoup

from .fetch_tools import DEFAULT_UA


def extract_dom_sample(url: str, use_browser: bool = False) -> dict[str, Any]:
    """Return a compact, agent-friendly sample of the page's DOM.

    Strips out <script>, <style>, comments, and SVG. Truncates to keep
    the agent's context window happy. Includes class/id frequency so
    the agent can spot repeating "item" containers.

    Args:
        url: Target URL.
        use_browser: If True, render with Playwright first (for SPAs).

    Returns:
        dict with keys: clean_html_sample, repeating_class_candidates,
        all_links_sample.
    """
    if use_browser:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_context(user_agent=DEFAULT_UA).new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(1500)
                html = page.content()
                browser.close()
        except Exception as e:
            return {"error": f"browser fetch failed: {e}"}
    else:
        try:
            r = requests.get(url, headers={"User-Agent": DEFAULT_UA}, timeout=20)
            html = r.text
        except Exception as e:
            return {"error": str(e)}

    soup = BeautifulSoup(html, "html.parser")

    # Strip noise
    for tag in soup(["script", "style", "svg", "noscript", "iframe"]):
        tag.decompose()

    # Find class names that appear many times — those are repeating item containers
    class_counts: dict[str, int] = {}
    for el in soup.find_all(class_=True):
        for c in el.get("class", []):
            class_counts[c] = class_counts.get(c, 0) + 1

    repeating = sorted(
        [(c, n) for c, n in class_counts.items() if 3 <= n <= 200],
        key=lambda kv: -kv[1],
    )[:20]

    # Sample links
    links = [a.get("href") for a in soup.find_all("a", href=True)][:30]

    body = soup.body or soup
    sample = str(body)[:10000]

    return {
        "clean_html_sample": sample,
        "repeating_class_candidates": [
            {"class": c, "count": n} for c, n in repeating
        ],
        "links_sample": links,
    }


def test_css_selector(
    url: str,
    container_selector: str,
    field_selector: str,
    method: str = "text",
    use_browser: bool = False,
) -> dict[str, Any]:
    """Test a (container, field) selector pair against a live page.

    Args:
        url: Target URL.
        container_selector: CSS selector for the repeating item.
        field_selector: CSS selector for the field WITHIN the container.
                        Pass "" to extract from the container itself.
        method: "text" or "attr:<name>".
        use_browser: Use Playwright instead of plain requests.

    Returns:
        dict with keys: match_count, sample_values (up to 5),
        success (bool — true if ≥1 non-empty value found).
    """
    if use_browser:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_context(user_agent=DEFAULT_UA).new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(1500)
                html = page.content()
                browser.close()
        except Exception as e:
            return {"error": str(e), "success": False}
    else:
        try:
            r = requests.get(url, headers={"User-Agent": DEFAULT_UA}, timeout=20)
            html = r.text
        except Exception as e:
            return {"error": str(e), "success": False}

    soup = BeautifulSoup(html, "html.parser")
    containers = soup.select(container_selector)

    samples: list[str] = []
    for c in containers[:10]:
        target = c.select_one(field_selector) if field_selector else c
        if target is None:
            continue
        if method == "text":
            val = target.get_text(strip=True)
        elif method.startswith("attr:"):
            attr = method.split(":", 1)[1]
            val = target.get(attr, "")
        else:
            val = ""
        if val:
            samples.append(val[:200])

    return {
        "match_count": len(containers),
        "sample_values": samples[:5],
        "success": bool(samples),
    }


def extract_json_paths(api_url: str, params: dict | None = None) -> dict[str, Any]:
    """Hit a JSON API endpoint and return its structure as a list of paths.

    Args:
        api_url: The endpoint URL.
        params: Optional query params.

    Returns:
        dict with keys: paths (list of dotted paths to leaf values),
        sample_response (truncated).
    """
    try:
        r = requests.get(
            api_url,
            params=params or {},
            headers={"User-Agent": DEFAULT_UA, "Accept": "application/json"},
            timeout=20,
        )
        data = r.json()
    except Exception as e:
        return {"error": str(e), "paths": []}

    paths: list[str] = []

    def walk(obj, prefix=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                walk(v, f"{prefix}.{k}" if prefix else k)
        elif isinstance(obj, list):
            if obj:
                walk(obj[0], f"{prefix}[*]")
            else:
                paths.append(f"{prefix}[]")
        else:
            paths.append(f"{prefix} = {type(obj).__name__}")

    walk(data)
    return {
        "paths": paths[:200],
        "sample_response": json.dumps(data)[:2000],
    }
