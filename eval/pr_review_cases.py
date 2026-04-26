"""
Eval cases for the Code Reviewer agent.
Tests that the agent correctly identifies code quality issues in PR diffs.

Run with:
    python scripts/run_eval.py --suite pr
"""
from eval.metrics import EvalCase

PR_REVIEW_CASES: list[EvalCase] = [

    EvalCase(
        case_id="pr-001-redis-leak",
        input={
            "repo": "org/api-server",
            "pr_number": 42,
            "description": "PR adds a Redis cache layer with a new connection per call (no pooling)",
        },
        expected_keywords=[
            # Agent must flag the connection leak
            "redis",
            "connection",
            # Agent must flag it as a risk
            "leak",            # or "pool" or "pooling"
        ],
        forbidden_keywords=[
            "no issues",       # agent should not give a clean bill of health
            "looks good",
        ],
    ),

    EvalCase(
        case_id="pr-002-hardcoded-ttl",
        input={
            "repo": "org/api-server",
            "pr_number": 42,
            "description": "PR hardcodes CACHE_TTL = 300 with no env var or config",
        },
        expected_keywords=[
            "hardcoded",       # or "hard-coded" or "magic number"
            "config",          # agent should suggest moving to config/env
        ],
        forbidden_keywords=[],
    ),

    EvalCase(
        case_id="pr-003-ci-failures",
        input={
            "repo": "org/api-server",
            "pr_number": 42,
            "description": "PR has failing integration tests and a failing build step in CI",
        },
        expected_keywords=[
            "integration",     # agent must notice failing integration tests
            "fail",            # or "failing" or "failed"
            "ci",              # or "pipeline" or "checks"
        ],
        forbidden_keywords=[
            "all tests pass",
            "green",
        ],
    ),

    EvalCase(
        case_id="pr-004-missing-test",
        input={
            "repo": "org/api-server",
            "pr_number": 42,
            "description": "cache.py has 80 lines added but only 5 lines of tests added",
        },
        expected_keywords=[
            "test",            # agent must notice the coverage gap
            "coverage",        # or "gap" or "missing"
        ],
        forbidden_keywords=[],
    ),

    EvalCase(
        case_id="pr-005-type-improvement",
        input={
            "repo": "org/api-server",
            "pr_number": 42,
            "description": "authenticate() changed to add type hints — low risk change",
        },
        expected_keywords=[
            "type",            # agent should acknowledge the type annotation change
        ],
        forbidden_keywords=[
            "critical",        # type hints alone are not critical
            "high risk",
        ],
    ),

]
