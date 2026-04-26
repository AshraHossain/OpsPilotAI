"""
OpsPilot AI — FastAPI entrypoint.
Handles webhook ingestion, workflow dispatch, the approval gate,
Prometheus metrics scraping, and audit trail queries.
"""
import hashlib
import hmac
import os
import uuid
import time

import structlog
from fastapi import FastAPI, HTTPException, Header, Request, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from prometheus_client import (
    Counter, Histogram, Gauge,
    generate_latest, CONTENT_TYPE_LATEST,
)

from config.context import IncidentContext
from config.settings import get_settings
from audit.trail import AuditTrail
from workflows.crew import (
    run_pr_review,
    run_cicd_analysis,
    run_scaling_analysis,
    run_incident_response,
)

log = structlog.get_logger()
settings = get_settings()
_trail = AuditTrail()

app = FastAPI(
    title="OpsPilot AI",
    description=(
        "Multi-agent DevOps control plane: PR review, CI/CD monitoring, "
        "infra scaling, incident response."
    ),
    version="0.2.0",
)

# ── Prometheus metrics ────────────────────────────────────────────────────────

WORKFLOW_COUNTER = Counter(
    "opspilot_incidents_total",
    "Total workflow invocations",
    ["workflow", "outcome"],
)
WORKFLOW_LATENCY = Histogram(
    "opspilot_workflow_duration_seconds",
    "Workflow execution latency",
    ["workflow"],
    buckets=[1, 5, 10, 30, 60, 120, 300],
)
APPROVAL_QUEUE = Gauge(
    "opspilot_approval_queue_size",
    "Number of incidents awaiting approval decision",
)
AUDIT_EVENTS = Counter(
    "opspilot_audit_events_total",
    "Total audit events logged",
    ["workflow", "outcome"],
)

# Simple in-memory approval store (replace with Redis/DynamoDB in production)
_approval_store: dict[str, dict] = {}


# ── Pydantic models ───────────────────────────────────────────────────────────

class WebhookPayload(BaseModel):
    event_type: str
    repo: str
    pr_number: int | None = None
    workflow_run_id: str | None = None
    deployment_name: str | None = None
    environment: str = "production"
    alert_ids: list[str] = []


class ApprovalRequest(BaseModel):
    incident_id: str
    approved: bool
    approver: str


# ── Health + metrics ──────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "OpsPilot AI",
        "version": "0.2.0",
        "approval_queue": len([v for v in _approval_store.values() if v.get("pending")]),
    }


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    """Prometheus scrape endpoint — exposes all opspilot_* metrics."""
    return PlainTextResponse(
        content=generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )


# ── Audit trail query ─────────────────────────────────────────────────────────

@app.get("/audit")
def get_audit_events(
    incident_id: str | None = Query(default=None, description="Filter by incident ID"),
    limit: int = Query(default=20, ge=1, le=200, description="Max events to return"),
):
    """
    Query the audit trail.
    - In development: reads from local audit_trail.jsonl
    - In production: query DynamoDB or S3 directly (see audit/trail.py)
    """
    try:
        events = _trail.get_events(incident_id=incident_id, limit=limit)
    except NotImplementedError:
        raise HTTPException(
            status_code=501,
            detail=(
                "Audit query via API is only supported for the local backend. "
                "Query DynamoDB or S3 directly in production."
            ),
        )
    return {
        "count": len(events),
        "backend": os.getenv("AUDIT_BACKEND", "local"),
        "events": events,
    }


# ── Webhook ingestion ─────────────────────────────────────────────────────────

@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(default=""),
    x_hub_signature_256: str = Header(default=""),
):
    """Ingests GitHub PR and workflow events and dispatches to the right agent workflow."""
    raw_body = await request.body()
    _verify_github_signature(raw_body, x_hub_signature_256)
    payload = await request.json()

    incident_id = str(uuid.uuid4())

    if x_github_event == "pull_request" and payload.get("action") in ("opened", "synchronize"):
        ctx = IncidentContext(
            incident_id=incident_id,
            repo=payload["repository"]["full_name"],
            pr_number=payload["pull_request"]["number"],
        )
        log.info("PR review triggered", incident_id=incident_id, pr=ctx.pr_number)
        t0 = time.time()
        result = run_pr_review(ctx)
        elapsed = time.time() - t0
        WORKFLOW_COUNTER.labels(workflow="pr_review", outcome="completed").inc()
        WORKFLOW_LATENCY.labels(workflow="pr_review").observe(elapsed)
        AUDIT_EVENTS.labels(workflow="pr_review", outcome="completed").inc()
        return {"incident_id": incident_id, "action": "pr_review", "result": result}

    if x_github_event == "workflow_run" and payload.get("action") == "completed":
        run = payload["workflow_run"]
        if run["conclusion"] == "failure":
            ctx = IncidentContext(
                incident_id=incident_id,
                repo=payload["repository"]["full_name"],
                workflow_run_id=str(run["id"]),
                deployment_name=run.get("head_repository", {}).get("name", ""),
            )
            log.info("CI/CD failure detected", incident_id=incident_id, run_id=ctx.workflow_run_id)
            t0 = time.time()
            result = run_cicd_analysis(ctx)
            elapsed = time.time() - t0
            WORKFLOW_COUNTER.labels(workflow="cicd_analysis", outcome="completed").inc()
            WORKFLOW_LATENCY.labels(workflow="cicd_analysis").observe(elapsed)
            AUDIT_EVENTS.labels(workflow="cicd_analysis", outcome="completed").inc()
            return {"incident_id": incident_id, "action": "cicd_analysis", "result": result}

    return {"incident_id": incident_id, "action": "ignored", "event": x_github_event}


@app.post("/webhook/alertmanager")
async def alertmanager_webhook(payload: dict):
    """Ingests grouped Alertmanager alerts and triggers incident response."""
    incident_id = str(uuid.uuid4())
    alerts = payload.get("alerts", [])
    alert_ids = [a.get("fingerprint", "") for a in alerts]
    deployment_name = alerts[0].get("labels", {}).get("deployment", "") if alerts else ""

    ctx = IncidentContext(
        incident_id=incident_id,
        repo=alerts[0].get("labels", {}).get("repo", "") if alerts else "",
        deployment_name=deployment_name,
        alert_ids=alert_ids,
        environment=alerts[0].get("labels", {}).get("env", "production") if alerts else "production",
    )

    # Mark as pending approval before running
    _approval_store[incident_id] = {"pending": True, "approved": None, "approver": None}
    APPROVAL_QUEUE.set(len([v for v in _approval_store.values() if v.get("pending")]))

    log.info("Alert incident triggered", incident_id=incident_id, alerts=len(alerts))
    t0 = time.time()
    result = run_incident_response(ctx)
    elapsed = time.time() - t0
    WORKFLOW_COUNTER.labels(workflow="incident_response", outcome="pending_approval").inc()
    WORKFLOW_LATENCY.labels(workflow="incident_response").observe(elapsed)
    AUDIT_EVENTS.labels(workflow="incident_response", outcome="pending_approval").inc()
    return {
        "incident_id": incident_id,
        "action": "incident_response",
        "status": "pending_approval",
        "result": result,
    }


# ── Manual triggers ───────────────────────────────────────────────────────────

@app.post("/trigger/scale-analysis")
async def trigger_scale_analysis(payload: WebhookPayload):
    """Manually trigger infrastructure scaling analysis."""
    incident_id = str(uuid.uuid4())
    ctx = IncidentContext(
        incident_id=incident_id,
        repo=payload.repo,
        deployment_name=payload.deployment_name or "",
        environment=payload.environment,
    )
    t0 = time.time()
    result = run_scaling_analysis(ctx)
    elapsed = time.time() - t0
    WORKFLOW_COUNTER.labels(workflow="scaling_analysis", outcome="completed").inc()
    WORKFLOW_LATENCY.labels(workflow="scaling_analysis").observe(elapsed)
    AUDIT_EVENTS.labels(workflow="scaling_analysis", outcome="completed").inc()
    return {"incident_id": incident_id, "action": "scaling_analysis", "result": result}


# ── Approval gate ─────────────────────────────────────────────────────────────

@app.post("/approve")
async def approve_action(req: ApprovalRequest):
    """Grant or deny a pending remediation action."""
    _approval_store[req.incident_id] = {
        "pending": False,
        "approved": req.approved,
        "approver": req.approver,
    }
    APPROVAL_QUEUE.set(len([v for v in _approval_store.values() if v.get("pending")]))
    outcome = "approved" if req.approved else "denied"
    WORKFLOW_COUNTER.labels(workflow="approval_gate", outcome=outcome).inc()
    log.info(
        "Approval decision recorded",
        incident_id=req.incident_id,
        approved=req.approved,
        approver=req.approver,
    )
    return {
        "incident_id": req.incident_id,
        "approved": req.approved,
        "approver": req.approver,
    }


@app.get("/approve/{incident_id}")
async def get_approval_status(incident_id: str):
    """Check whether a specific incident has been approved."""
    record = _approval_store.get(incident_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Incident not found or no decision made.")
    return {
        "incident_id": incident_id,
        "pending": record.get("pending", False),
        "approved": record.get("approved"),
        "approver": record.get("approver"),
    }


@app.get("/approve")
async def list_pending_approvals():
    """List all incidents currently awaiting an approval decision."""
    pending = [
        {"incident_id": iid, **data}
        for iid, data in _approval_store.items()
        if data.get("pending")
    ]
    return {"pending_count": len(pending), "incidents": pending}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _verify_github_signature(body: bytes, signature_header: str):
    secret = getattr(settings, "github_webhook_secret", "")
    if not secret:
        return  # skip in dev
    secret_bytes = secret.encode() if isinstance(secret, str) else secret
    expected = "sha256=" + hmac.new(secret_bytes, body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature_header):
        raise HTTPException(status_code=401, detail="Invalid GitHub webhook signature.")
