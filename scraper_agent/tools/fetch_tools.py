"""
Tools for fetching and probing target websites.
"""
from __future__ import annotations

import json
import urllib.parse
from typing import Any
from urllib.robotparser import RobotFileParser

import requests


DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def fetch_static_html(url: str) -> dict[str, Any]:
    """Fetch a URL with plain HTTP and return the HTML body + metadata.

    Use this to determine whether a site is server-rendered. If the returned
    HTML is small or mostly <script> tags, the page is likely JS-rendered.

    Args:
        url: The fully-qualified target URL.

    Returns:
        dict with keys: status_code, content_length, html_sample, headers,
        looks_javascript_rendered (bool heuristic).
    """
    try:
        r = requests.get(url, headers={"User-Agent": DEFAULT_UA}, timeout=20)
    except Exception as e:
        return {"error": str(e), "status_code": None}

    html = r.text
    # Heuristic: very small body OR script-tag ratio > 50% suggests SPA
    script_chars = sum(
        len(s) for s in html.split("<script") if s
    ) - len(html.split("<script", 1)[0] if "<script" in html else "")
    body_chars = max(len(html), 1)
    js_ratio = script_chars / body_chars
    looks_js = (len(html) < 5000) or (js_ratio > 0.5 and "<div id=\"root\"" in html.lower()) \
        or "ng-app" in html.lower() or "data-reactroot" in html.lower()

    return {
        "status_code": r.status_code,
        "content_length": len(html),
        "html_sample": html[:8000],
        "headers": dict(r.headers),
        "looks_javascript_rendered": looks_js,
    }


def fetch_with_browser(url: str) -> dict[str, Any]:
    """Fetch a URL using a headless browser (Playwright) to get the rendered DOM.

    Use this when fetch_static_html returned an empty/SPA shell.

    Args:
        url: The fully-qualified target URL.

    Returns:
        dict with keys: status_code, html_sample (rendered DOM), title,
        captured_xhr_urls (list of API endpoints the page called).
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            "error": "playwright not installed in agent environment. "
                     "run: pip install playwright && playwright install chromium"
        }

    captured: list[str] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=DEFAULT_UA)
            page = context.new_page()

            page.on("request", lambda req: captured.append(req.url)
                    if req.resource_type in ("xhr", "fetch") else None)

            response = page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)  # let late XHRs settle

            html = page.content()
            title = page.title()
            status = response.status if response else None
            browser.close()

        return {
            "status_code": status,
            "title": title,
            "html_sample": html[:12000],
            "captured_xhr_urls": list(dict.fromkeys(captured))[:30],
        }
    except Exception as e:
        return {"error": str(e)}


def detect_json_apis(url: str) -> dict[str, Any]:
    """Open the page in a headless browser and capture every XHR/fetch call.

    These captured endpoints are often the easiest scraping target — they
    return JSON directly with no HTML parsing required.

    Args:
        url: The page URL to load.

    Returns:
        dict with keys: api_endpoints (list of {url, method, sample_response}).
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"error": "playwright not installed", "api_endpoints": []}

    endpoints: list[dict[str, Any]] = []
    seen: set[str] = set()

    def on_response(response):
        try:
            ct = response.headers.get("content-type", "")
            if "json" not in ct.lower():
                return
            key = f"{response.request.method} {response.url}"
            if key in seen:
                return
            seen.add(key)
            try:
                body = response.json()
                sample = json.dumps(body)[:1500]
            except Exception:
                sample = response.text()[:1500]
            endpoints.append({
                "url": response.url,
                "method": response.request.method,
                "status": response.status,
                "sample_response": sample,
            })
        except Exception:
            pass

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_context(user_agent=DEFAULT_UA).new_page()
            page.on("response", on_response)
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)
            browser.close()
    except Exception as e:
        return {"error": str(e), "api_endpoints": endpoints}

    # Rank endpoints — bigger JSON bodies are usually the data ones
    endpoints.sort(key=lambda e: len(e.get("sample_response", "")), reverse=True)
    return {"api_endpoints": endpoints[:15]}


def check_robots_txt(url: str) -> dict[str, Any]:
    """Check robots.txt for the given URL's host.

    Args:
        url: Any URL on the target site.

    Returns:
        dict with keys: allowed (bool for our default UA), crawl_delay,
        relevant_rules.
    """
    parsed = urllib.parse.urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = RobotFileParser()
    try:
        rp.set_url(robots_url)
        rp.read()
        allowed = rp.can_fetch(DEFAULT_UA, url)
        delay = rp.crawl_delay(DEFAULT_UA) or rp.crawl_delay("*")
        return {
            "robots_url": robots_url,
            "allowed": bool(allowed),
            "crawl_delay": delay,
        }
    except Exception as e:
        # No robots.txt or unreachable — default to allowed
        return {"robots_url": robots_url, "allowed": True, "error": str(e)}
