"""
Code Reviewer Agent
"""
from crewai import Agent
from config.settings import get_settings
from tools import get_tools


def build_code_reviewer_agent() -> Agent:
    return Agent(
        role="Code Reviewer",
        goal=(
            "Analyze pull request diffs, identify risky patterns, test gaps, and "
            "flaky-test signals. Produce a concise, actionable review summary."
        ),
        backstory=(
            "You are a senior software engineer with deep expertise in code quality, "
            "testing strategy, and CI hygiene. You review PRs the way a principal "
            "engineer would: clear, direct, and focused on what actually matters."
        ),
        llm=get_settings().agent_model,
        tools=get_tools("github"),
        verbose=True,
        allow_delegation=False,
    )
