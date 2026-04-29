"""
OpsPilot AI -- Demo Runner
==========================
Runs all 4 agent workflows with mock data so you can see every agent
fire and produce output.  Requires a running Ollama instance with the
gemma4:26b model pulled -- no cloud API keys needed.

Usage:
    python demo_runner.py                   # runs all 4 workflows
    python demo_runner.py --workflow pr     # PR review only
    python demo_runner.py --workflow ci     # CI/CD analysis only
    python demo_runner.py --workflow scale  # scaling analysis only
    python demo_runner.py --workflow incident  # incident response only

Requirements:
    - Ollama running locally (ollama serve)
    - Model pulled: ollama pull gemma4:26b
    - APP_ENV=development (default) -- uses mock tools automatically
"""
import argparse
import os
import time
from dotenv import load_dotenv

load_dotenv()

# Trigger settings load early so OLLAMA_API_BASE is exported before CrewAI init.
from config.settings import get_settings
get_settings()

os.environ.setdefault("APP_ENV", "development")

from config.context import IncidentContext
from workflows.crew import (
    run_pr_review,
    run_cicd_analysis,
    run_scaling_analysis,
    run_incident_response,
)

DIVIDER = "=" * 70


def banner(title):
    print("\n" + DIVIDER)
    print("  " + title)
    print(DIVIDER)


def run_demo_pr_review():
    banner("WORKFLOW 1 -- PR Code Review")
    ctx = IncidentContext(
        incident_id="demo-pr-001",
        repo="org/api-server",
        pr_number=42,
    )
    print("  PR #{} in {}\n".format(ctx.pr_number, ctx.repo))
    start = time.time()
    result = run_pr_review(ctx)
    elapsed = time.time() - start
    print("\n" + "-" * 70)
    print("  PR Review complete ({:.1f}s)".format(elapsed))
    print("-" * 70)
    print(result)


def run_demo_cicd_analysis():
    banner("WORKFLOW 2 -- CI/CD Failure Analysis")
    ctx = IncidentContext(
        incident_id="demo-ci-001",
        repo="org/api-server",
        workflow_run_id="9876543210",
        deployment_name="api-server",
        environment="production",
    )
    print("  Workflow run #{} in {}\n".format(ctx.workflow_run_id, ctx.repo))
    start = time.time()
    result = run_cicd_analysis(ctx)
    elapsed = time.time() - start
    print("\n" + "-" * 70)
    print("  CI/CD Analysis complete ({:.1f}s)".format(elapsed))
    print("-" * 70)
    print(result)


def run_demo_scaling_analysis():
    banner("WORKFLOW 3 -- Infrastructure Scaling Analysis")
    ctx = IncidentContext(
        incident_id="demo-scale-001",
        repo="org/api-server",
        deployment_name="api-server",
        environment="production",
    )
    print("  Deployment: {} in {}\n".format(ctx.deployment_name, ctx.environment))
    start = time.time()
    result = run_scaling_analysis(ctx)
    elapsed = time.time() - start
    print("\n" + "-" * 70)
    print("  Scaling Analysis complete ({:.1f}s)".format(elapsed))
    print("-" * 70)
    print(result)


def run_demo_incident_response():
    banner("WORKFLOW 4 -- Full Incident Response")
    ctx = IncidentContext(
        incident_id="demo-incident-001",
        repo="org/api-server",
        workflow_run_id="9876543210",
        deployment_name="api-server",
        environment="production",
        alert_ids=["alert-cpu-001", "alert-oom-002", "alert-crash-003"],
    )
    print("  Incident: {}".format(ctx.incident_id))
    print("  Deployment: {} | Alerts: {}\n".format(ctx.deployment_name, len(ctx.alert_ids)))
    start = time.time()
    result = run_incident_response(ctx)
    elapsed = time.time() - start
    print("\n" + "-" * 70)
    print("  Incident Response complete ({:.1f}s)".format(elapsed))
    print("-" * 70)
    print(result)


WORKFLOWS = {
    "pr": run_demo_pr_review,
    "ci": run_demo_cicd_analysis,
    "scale": run_demo_scaling_analysis,
    "incident": run_demo_incident_response,
}


def main():
    parser = argparse.ArgumentParser(description="OpsPilot AI -- Demo Runner")
    parser.add_argument(
        "--workflow",
        choices=list(WORKFLOWS.keys()),
        default=None,
        help="Run a specific workflow. Omit to run all four.",
    )
    args = parser.parse_args()

    settings = get_settings()
    print("\n" + "#" * 70)
    print("  OpsPilot AI -- Demo Mode (APP_ENV={})".format(os.getenv("APP_ENV")))
    print("  LLM: {}  (base: {})".format(settings.agent_model, settings.ollama_api_base))
    print("  All tools are mocked -- no real APIs called.")
    print("#" * 70)

    if args.workflow:
        WORKFLOWS[args.workflow]()
    else:
        for fn in WORKFLOWS.values():
            fn()
            print()

    print("\n" + "#" * 70)
    print("  Demo complete. Next steps:")
    print("  1. Set GITHUB_TOKEN + GITHUB_WEBHOOK_SECRET in .env")
    print("  2. Set APP_ENV=staging to switch to real tools")
    print("  3. Run: uvicorn api.main:app --reload")
    print("  4. python scripts/ngrok_start.py --repo your-username/your-repo")
    print("#" * 70 + "\n")


if __name__ == "__main__":
    main()
