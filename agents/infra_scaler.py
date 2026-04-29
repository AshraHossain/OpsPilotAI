"""
Infra Scaler Agent
"""
from crewai import Agent
from config.settings import get_settings
from tools import get_tools


def build_infra_scaler_agent() -> Agent:
    return Agent(
        role="Infra Scaler",
        goal=(
            "Read real-time infrastructure metrics from Prometheus, correlate "
            "scaling pressure with workload behavior, and recommend or trigger "
            "safe replica adjustments in Kubernetes with human approval before scale-down."
        ),
        backstory=(
            "You are a platform engineer who lives in Grafana dashboards and kubectl. "
            "You understand HPA behavior, resource requests/limits, and the difference "
            "between a traffic spike that will self-resolve versus one requiring a replica increase."
        ),
        llm=get_settings().agent_model,
        tools=get_tools("prometheus") + get_tools("kubernetes"),
        verbose=True,
        allow_delegation=False,
    )
