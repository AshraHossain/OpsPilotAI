"""
OpsPilot AI — CrewAI Crew definition.
Builds the four-agent crew and exposes workflow entry points.
All workflows are instrumented with the AuditTrail.
"""
import time

from crewai import Crew, Task
from agents.code_reviewer import build_code_reviewer_agent
from agents.cicd_monitor import build_cicd_monitor_agent
from agents.infra_scaler import build_infra_scaler_agent
from agents.incident_resolver import build_incident_resolver_agent
from config.context import IncidentContext
from audit.trail import AuditTrail

_trail = AuditTrail()


def _build_crew() -> Crew:
    return Crew(
        agents=[
            build_code_reviewer_agent(),
            build_cicd_monitor_agent(),
            build_infra_scaler_agent(),
            build_incident_resolver_agent(),
        ],
        verbose=True,
    )


# ── Workflow: PR Review ───────────────────────────────────────────────────────

def run_pr_review(ctx: IncidentContext) -> str:
    """Run the Code Reviewer agent against a pull request."""
    crew = _build_crew()
    reviewer = crew.agents[0]

    task = Task(
        description=(
            f"Review pull request #{ctx.pr_number} in repo '{ctx.repo}'. "
            "Fetch the diff, check CI results, flag risky changes, test gaps, "
            "and flaky-test signals. Return a concise markdown review summary."
        ),
        expected_output="Markdown review summary with risk ratings and suggested fixes.",
        agent=reviewer,
    )
    crew.tasks = [task]
    t0 = time.time()
    result = crew.kickoff()
    _trail.log(
        incident_id=ctx.incident_id,
        workflow="pr_review",
        repo=ctx.repo,
        outcome="completed",
        summary=str(result),
        duration_seconds=round(time.time() - t0, 2),
        metadata={"pr_number": ctx.pr_number},
    )
    return result


# ── Workflow: CI/CD Failure Analysis ─────────────────────────────────────────

def run_cicd_analysis(ctx: IncidentContext) -> str:
    """Run the CI/CD Monitor + Incident Resolver on a failed pipeline run."""
    crew = _build_crew()
    monitor = crew.agents[1]
    resolver = crew.agents[3]

    monitor_task = Task(
        description=(
            f"Analyze the failed GitHub Actions workflow run {ctx.workflow_run_id} "
            f"in repo '{ctx.repo}'. Identify the failing step and summarize the error."
        ),
        expected_output="Root-cause summary of the failed pipeline step.",
        agent=monitor,
    )

    resolver_task = Task(
        description=(
            "Given the CI/CD failure summary above, correlate with active Alertmanager "
            f"alerts and pod events for deployment '{ctx.deployment_name}' in namespace "
            f"'{ctx.environment}'. Recommend rollback, restart, or rerun, and draft "
            "a GitHub issue body for tracking."
        ),
        expected_output="Recommended remediation action + draft GitHub issue body.",
        agent=resolver,
        context=[monitor_task],
    )

    crew.tasks = [monitor_task, resolver_task]
    t0 = time.time()
    result = crew.kickoff()
    _trail.log(
        incident_id=ctx.incident_id,
        workflow="cicd_analysis",
        repo=ctx.repo,
        outcome="completed",
        summary=str(result),
        duration_seconds=round(time.time() - t0, 2),
        metadata={"workflow_run_id": ctx.workflow_run_id, "deployment": ctx.deployment_name},
    )
    return result


# ── Workflow: Infra Scaling Analysis ─────────────────────────────────────────

def run_scaling_analysis(ctx: IncidentContext) -> str:
    """Run the Infra Scaler agent to assess and recommend scaling."""
    crew = _build_crew()
    scaler = crew.agents[2]

    task = Task(
        description=(
            f"Query Prometheus for CPU, memory, latency, and error-rate metrics "
            f"for deployment '{ctx.deployment_name}'. Correlate with active alerts. "
            "Return a scaling recommendation including target replica count and rationale."
        ),
        expected_output="Scaling recommendation with target replicas and confidence level.",
        agent=scaler,
    )
    crew.tasks = [task]
    t0 = time.time()
    result = crew.kickoff()
    _trail.log(
        incident_id=ctx.incident_id,
        workflow="scaling_analysis",
        repo=ctx.repo,
        outcome="completed",
        summary=str(result),
        duration_seconds=round(time.time() - t0, 2),
        metadata={"deployment": ctx.deployment_name, "environment": ctx.environment},
    )
    return result


# ── Workflow: Full Incident Response ─────────────────────────────────────────

def run_incident_response(ctx: IncidentContext) -> str:
    """Run the full incident response pipeline across all relevant agents."""
    crew = _build_crew()
    monitor = crew.agents[1]
    scaler = crew.agents[2]
    resolver = crew.agents[3]

    monitor_task = Task(
        description=(
            f"Fetch and summarize the GitHub Actions run {ctx.workflow_run_id} "
            f"in '{ctx.repo}' — identify the failing stage."
        ),
        expected_output="CI/CD failure summary.",
        agent=monitor,
    )

    scaler_task = Task(
        description=(
            f"Query Prometheus metrics for '{ctx.deployment_name}' and check if "
            "resource pressure contributed to the incident."
        ),
        expected_output="Metrics summary and whether scaling contributed to the incident.",
        agent=scaler,
        context=[monitor_task],
    )

    resolver_task = Task(
        description=(
            "Using the CI/CD failure summary and metrics analysis above, correlate "
            "with Alertmanager alerts and Kubernetes pod events. "
            "Produce: (1) a root-cause statement, (2) recommended action with approval "
            "flag, (3) a draft RCA in markdown."
        ),
        expected_output="Root-cause analysis + recommended action + draft RCA.",
        agent=resolver,
        context=[monitor_task, scaler_task],
    )

    crew.tasks = [monitor_task, scaler_task, resolver_task]
    t0 = time.time()
    result = crew.kickoff()
    _trail.log(
        incident_id=ctx.incident_id,
        workflow="incident_response",
        repo=ctx.repo,
        outcome="completed",
        summary=str(result),
        duration_seconds=round(time.time() - t0, 2),
        metadata={
            "deployment": ctx.deployment_name,
            "environment": ctx.environment,
            "alert_ids": ctx.alert_ids,
        },
    )
    return result
