"""
Root Web Scraping Agent
Orchestrates sub-agents to analyze websites and generate standalone scrapers.
"""
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools.agent_tool import AgentTool

from .sub_agents.site_analyzer import site_analyzer_agent
from .sub_agents.strategy_planner import strategy_planner_agent
from .sub_agents.selector_extractor import selector_extractor_agent
from .sub_agents.code_generator import code_generator_agent
from .sub_agents.validator import validator_agent


# Sequential pipeline: analyze -> plan -> extract selectors -> generate -> validate
scraping_pipeline = SequentialAgent(
    name="scraping_pipeline",
    description="Pipeline that analyzes a site and produces a standalone scraper.",
    sub_agents=[
        site_analyzer_agent,
        strategy_planner_agent,
        selector_extractor_agent,
        code_generator_agent,
        validator_agent,
    ],
)


root_agent = LlmAgent(
    name="web_scraping_orchestrator",
    model="gemini-2.0-flash",
    description=(
        "Root agent that takes a URL and a natural-language description of what "
        "to scrape, then produces a standalone, self-contained Python scraper script."
    ),
    instruction="""You are a web-scraping orchestrator agent.

INPUT FROM USER:
  1. A target website URL
  2. A description of what data to scrape (e.g. "all product names, prices, ratings")

YOUR JOB:
  - Validate that the user provided BOTH a URL and a description.
  - If anything is missing, ask for it. Do not guess.
  - Once you have both, hand the task off to the `scraping_pipeline` tool.
  - The pipeline will return the path to a generated standalone Python script
    plus a short summary of how it works.
  - Present that path and summary to the user. Tell them they can run the
    script directly with `python <script>.py` and it will scrape WITHOUT
    needing the agent.

RULES:
  - Never write scraper code yourself — always delegate to the pipeline.
  - Refuse sites that are obviously off-limits (auth-walled banking, sites
    whose ToS forbid scraping when the user has flagged it, anything
    requiring credentials you don't have).
  - Remind the user to respect robots.txt and rate limits.
""",
    tools=[AgentTool(agent=scraping_pipeline)],
)
