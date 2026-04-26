"""
Eval cases for the CI/CD Monitor agent.
Tests that the agent correctly identifies failed pipeline steps and root causes.

Run with:
    python scripts/run_eval.py --suite cicd
"""
from eval.metrics import EvalCase

CICD_CASES: list[EvalCase] = [

    EvalCase(
        case_id="cicd-001-postgres-missing",
        input={
            "repo": "org/api-server",
            "run_id": 9876543210,
            "description": "Integration tests failed: ConnectionRefusedError on port 5432 — no postgres service declared",
        },
        expected_keywords=[
            "integration",          # agent must identify the failed job
            "postgres",             # or "database" or "connection"
            "connection",           # root cause involves connection failure
        ],
        forbidden_keywords=[
            "lint",                 # lint passed — agent should not blame lint
            "build",                # build was skipped, not the root cause
        ],
    ),

    EvalCase(
        case_id="cicd-002-oom",
        input={
            "repo": "org/api-server",
            "run_id": 9876543211,
            "description": "Build step failed: OOMKilled — container allocated 512MB cache at startup",
        },
        expected_keywords=[
            "memory",               # or "oom" or "out of memory"
            "build",                # the build job failed
        ],
        forbidden_keywords=[
            "test",                 # tests did not cause this failure
        ],
    ),

    EvalCase(
        case_id="cicd-003-root-cause-step",
        input={
            "repo": "org/api-server",
            "run_id": 9876543210,
            "description": "Workflow run with jobs: lint(pass), unit-tests(pass), integration-tests(fail), deploy(skip)",
        },
        expected_keywords=[
            "integration",          # agent must pinpoint the integration-tests step
            "deploy",               # agent should note deploy was skipped as a consequence
            "rerun",                # or "rollback" or "fix" — agent must suggest next action
        ],
        forbidden_keywords=[
            "unit",                 # unit tests passed — not the culprit
        ],
    ),

    EvalCase(
        case_id="cicd-004-escalation",
        input={
            "repo": "org/api-server",
            "run_id": 9876543212,
            "description": "5 consecutive workflow runs have failed — repeated OOMKilled in the build step",
        },
        expected_keywords=[
            "escalat",              # agent should recommend escalation (escalate/escalation)
            "incident",             # or "resolver" — agent should suggest handing off to Incident Resolver
        ],
        forbidden_keywords=[
            "ignore",
        ],
    ),

    EvalCase(
        case_id="cicd-005-rerun-safe",
        input={
            "repo": "org/api-server",
            "run_id": 9876543213,
            "description": "Integration test failed once due to a flaky test (random seed issue) — first occurrence",
        },
        expected_keywords=[
            "rerun",                # agent should suggest a safe rerun first
            "flaky",                # or "transient" or "intermittent"
        ],
        forbidden_keywords=[
            "rollback",             # rollback is too aggressive for a single flaky test
        ],
    ),

]
