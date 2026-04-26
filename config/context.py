"""
Shared incident context object passed between all agents.
Keeps the system stateless per-request while still sharing signal data.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class IncidentContext:
    """Normalized context object built by the API layer and shared across agents."""

    # Identifiers
    incident_id: str = ""
    repo: str = ""               # e.g. "org/repo"
    environment: str = "production"

    # CI/CD signals
    workflow_run_id: Optional[str] = None
    failed_step: Optional[str] = None
    pipeline_logs: Optional[str] = None

    # PR signals
    pr_number: Optional[int] = None
    pr_diff: Optional[str] = None

    # Observability signals
    alert_ids: list[str] = field(default_factory=list)
    prometheus_metrics: Optional[dict] = None

    # Kubernetes signals
    pod_events: Optional[str] = None
    deployment_name: Optional[str] = None

    # Agent outputs
    suspected_root_cause: Optional[str] = None
    recommended_actions: list[str] = field(default_factory=list)

    # Approval gate
    pending_approval: bool = False
    approved: Optional[bool] = None
