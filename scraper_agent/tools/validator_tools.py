"""
Tools that smoke-test the generated scraper script.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def run_generated_script(
    script_path: str,
    max_pages: int = 1,
    timeout_seconds: int = 60,
) -> dict[str, Any]:
    """Run a generated scraper as a subprocess with --max-pages 1 to smoke-test.

    Args:
        script_path: Absolute path to the generated .py file.
        max_pages: How many pages of pagination to allow during the test.
        timeout_seconds: Hard timeout for the subprocess.

    Returns:
        dict with keys: returncode, stdout_tail, stderr_tail, output_path,
        ran_successfully.
    """
    script = Path(script_path)
    if not script.exists():
        return {"error": f"script not found: {script_path}", "ran_successfully": False}

    output_path = script.parent / f"{script.stem}_test_output.json"

    try:
        proc = subprocess.run(
            [
                sys.executable,
                str(script),
                "--max-pages", str(max_pages),
                "--output", str(output_path),
                "--format", "json",
            ],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=str(script.parent),
        )
    except subprocess.TimeoutExpired as e:
        return {
            "ran_successfully": False,
            "error": f"timeout after {timeout_seconds}s",
            "stderr_tail": (e.stderr or "")[-2000:],
        }

    return {
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
        "output_path": str(output_path),
        "ran_successfully": proc.returncode == 0 and output_path.exists(),
    }


def inspect_output(output_path: str, max_rows: int = 3) -> dict[str, Any]:
    """Read the test output and report what's inside.

    Args:
        output_path: Path to the JSON output file from the test run.
        max_rows: How many sample rows to return.

    Returns:
        dict with keys: row_count, fields, empty_field_ratio, sample_rows.
    """
    path = Path(output_path)
    if not path.exists():
        return {"error": "output file does not exist", "row_count": 0}

    try:
        data = json.loads(path.read_text())
    except Exception as e:
        return {"error": f"could not parse output as JSON: {e}", "row_count": 0}

    if not isinstance(data, list):
        data = [data]

    if not data:
        return {"row_count": 0, "fields": [], "sample_rows": []}

    fields = list(data[0].keys()) if isinstance(data[0], dict) else []

    # Count empty fields per row
    empty_counts: dict[str, int] = {f: 0 for f in fields}
    for row in data:
        if not isinstance(row, dict):
            continue
        for f in fields:
            v = row.get(f)
            if v in (None, "", [], {}):
                empty_counts[f] += 1

    n = len(data)
    empty_ratio = {f: round(empty_counts[f] / n, 2) for f in fields}

    return {
        "row_count": n,
        "fields": fields,
        "empty_field_ratio": empty_ratio,
        "sample_rows": data[:max_rows],
    }
