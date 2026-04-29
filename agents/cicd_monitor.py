"""
CI/CD Monitor Agent
"""
from crewai import Agent
from config.settings import get_settings
from tools import get_tools


def build_cicd_monitor_agent() -> Agent:
    return Agent(
        role="CI/CD Monitor",
        goal=(
            "Detect failed CI/CD pipeline stages, read job and step-level logs, "
            "summarize the likely failure point, and suggest whether to rerun, "
            "roll back, or escalate to the Incident Resolver."
        ),
        backstory=(
            "You are a release engineering specialist who has debugged thousands of "
            "pipeline failures. You cut through log noise to find the exact step and "
            "error that caused a build to break, and you know when a fix is simple "
            "versus when it signals a deeper infrastructure problem."
        ),
        llm=get_settings().agent_model,
        tools=get_tools("github"),
        verbose=True,
        allow_delegation=False,
    )
