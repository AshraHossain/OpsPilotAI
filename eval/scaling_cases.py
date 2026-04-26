"""
Eval cases for the Infra Scaler agent.
Tests that the agent correctly reads Prometheus metrics and produces
accurate, proportionate scaling recommendations.

Run with:
    python scripts/run_eval.py --suite scaling
"""
from eval.metrics import EvalCase

SCALING_CASES = [

    EvalCase(
        case_id="scale-001-cpu-spike",
        input={
            "deployment_name": "sample-api",
            "description": "CPU at 87% for 10 minutes on all pods; HPA max not yet reached; traffic spike in progress",
        },
        expected_keywords=[
            "scale",           # agent must recommend scaling up
            "replica",         # or "replicas" -- agent must specify target
            "cpu",             # agent must reference the CPU metric
        ],
        forbidden_keywords=[
            "scale down",      # should not scale down during a spike
            "reduce",
        ],
    ),

    EvalCase(
        case_id="scale-002-memory-pressure",
        input={
            "deployment_name": "sample-api",
            "description": "Memory at 91% of limit; CPU normal at 30%; 2 of 3 pods showing pressure",
        },
        expected_keywords=[
            "memory",
            "limit",           # agent should mention the memory limit
        ],
        forbidden_keywords=[
            "cpu",             # CPU is not the issue here
        ],
    ),

    EvalCase(
        case_id="scale-003-false-positive",
        input={
            "deployment_name": "sample-api",
            "description": "CPU spike to 85% for 90 seconds, now back to 20%; single pod; traffic normal",
        },
        expected_keywords=[
            "transient",       # or "temporary" or "resolved" -- agent should not overreact
        ],
        forbidden_keywords=[
            "scale up",        # a 90-second spike that resolved does not need scaling
            "increase replica",
        ],
    ),

    EvalCase(
        case_id="scale-004-approval-required",
        input={
            "deployment_name": "sample-api",
            "description": "CPU at 20%, memory at 25%; agent recommends scale-down from 4 to 1 replica",
        },
        expected_keywords=[
            "approv",          # scale-down always needs approval
            "human",           # or "gate"
        ],
        forbidden_keywords=[
            "automatically scaled down",
        ],
    ),

    EvalCase(
        case_id="scale-005-recommendation-format",
        input={
            "deployment_name": "sample-api",
            "description": "CPU at 78%, memory at 60%; currently 2 replicas; HPA max is 8",
        },
        expected_keywords=[
            "replica",         # agent must state a replica count
            "recommend",       # or "suggest"
            "cpu",
        ],
        forbidden_keywords=[
            "insufficient data",
        ],
    ),

]
