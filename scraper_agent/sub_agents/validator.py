"""
Validator Agent
Runs the generated script against the live site with --max-pages 1
and checks that it actually produces non-empty output.
"""
from google.adk.agents import LlmAgent

from ..tools.validator_tools import run_generated_script, inspect_output


validator_agent = LlmAgent(
    name="validator",
    model="gemini-2.0-flash",
    description="Smoke-tests the generated scraper script and reports results.",
    instruction="""You validate the generated scraper.

Read `generated_script_path` from session state.

STEPS:
  1. Call `run_generated_script(generated_script_path, max_pages=1)`.
     This runs the script in a subprocess with a 60-second timeout.
  2. Call `inspect_output(output_path)` to look at the produced data.
  3. Decide PASS or FAIL:
       PASS = script ran without errors AND output has at least 1 row
              AND each row has at least one non-empty field.
       FAIL = anything else.

  4. If FAIL, write a clear diagnosis under session state `validation_report`:
       - what error occurred
       - which fields came back empty
       - a concrete suggestion (e.g. "selector for price returns nothing,
         try `.price-tag` instead of `.price`")

  5. If PASS, write a short success report and a sample of the first 3 rows.

Set session state `validation_status` to "PASS" or "FAIL".

Finally, present the user with:
  - the absolute path to the script
  - whether validation passed
  - the pip install command they need
  - a one-liner showing how to run it
""",
    tools=[run_generated_script, inspect_output],
    output_key="validation_report",
)
