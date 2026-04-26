"""
run_eval.py
===========
Runs all eval suites against live agent workflows and prints a precision/recall report.

Usage:
    python scripts/run_eval.py                   # all suites
    python scripts/run_eval.py --suite pr        # PR review
    python scripts/run_eval.py --suite cicd      # CI/CD monitor
    python scripts/run_eval.py --suite incident  # Incident Resolver
    python scripts/run_eval.py --suite scaling   # Infra Scaler
    python scripts/run_eval.py --dry-run         # print cases, no LLM calls

Requirements:
    GOOGLE_API_KEY set in .env
    APP_ENV=development (mock tools) or staging (real APIs)
"""
import argparse
import os
import sys
import time

from dotenv import load_dotenv
load_dotenv()

os.environ.setdefault("APP_ENV", "development")

if not os.getenv("GOOGLE_API_KEY"):
    print("ERROR: GOOGLE_API_KEY not set in .env")
    print("   Get a free key at: https://aistudio.google.com/app/apikey")
    sys.exit(1)

from config.context import IncidentContext
from eval.metrics import evaluate, print_eval_report
from eval.pr_review_cases import PR_REVIEW_CASES
from eval.cicd_cases import CICD_CASES
from eval.incident_cases import INCIDENT_CASES
from eval.scaling_cases import SCALING_CASES


def pr_review_adapter(input_dict):
    from workflows.crew import run_pr_review
    ctx = IncidentContext(
        incident_id="eval-{}".format(input_dict.get("pr_number", 0)),
        repo=input_dict.get("repo", "org/repo"),
        pr_number=input_dict.get("pr_number", 1),
    )
    return run_pr_review(ctx)


def cicd_adapter(input_dict):
    from workflows.crew import run_cicd_analysis
    ctx = IncidentContext(
        incident_id="eval-{}".format(input_dict.get("run_id", 0)),
        repo=input_dict.get("repo", "org/repo"),
        workflow_run_id=str(input_dict.get("run_id", 0)),
        deployment_name="api-server",
    )
    return run_cicd_analysis(ctx)


def incident_adapter(input_dict):
    from workflows.crew import run_incident_response
    ctx = IncidentContext(
        incident_id="eval-inc-{}".format(input_dict.get("deployment_name", "app")),
        repo=input_dict.get("repo", "org/repo"),
        deployment_name=input_dict.get("deployment_name", "api-server"),
        environment="production",
        alert_ids=["PodCrashLooping", "HighMemoryPressure"],
    )
    return run_incident_response(ctx)


def scaling_adapter(input_dict):
    from workflows.crew import run_scaling_analysis
    ctx = IncidentContext(
        incident_id="eval-scale-{}".format(input_dict.get("deployment_name", "app")),
        repo=input_dict.get("repo", "org/repo"),
        deployment_name=input_dict.get("deployment_name", "api-server"),
        environment="production",
    )
    return run_scaling_analysis(ctx)


SUITES = {
    "pr": {
        "name": "PR Code Review",
        "cases": PR_REVIEW_CASES,
        "adapter": pr_review_adapter,
        "target_pass_rate": 0.80,
    },
    "cicd": {
        "name": "CI/CD Failure Detection",
        "cases": CICD_CASES,
        "adapter": cicd_adapter,
        "target_pass_rate": 0.90,
    },
    "incident": {
        "name": "Incident Resolver",
        "cases": INCIDENT_CASES,
        "adapter": incident_adapter,
        "target_pass_rate": 0.80,
    },
    "scaling": {
        "name": "Infra Scaler",
        "cases": SCALING_CASES,
        "adapter": scaling_adapter,
        "target_pass_rate": 0.80,
    },
}


def run_suite(suite_key, dry_run=False):
    suite = SUITES[suite_key]
    print("\n" + "#" * 60)
    print("  Suite: {}".format(suite["name"]))
    print("  Cases: {}  |  Target: {:.0f}%".format(
        len(suite["cases"]), suite["target_pass_rate"] * 100))
    print("#" * 60)

    if dry_run:
        for case in suite["cases"]:
            print("\n  [{}]".format(case.case_id))
            print("    Must contain : {}".format(case.expected_keywords))
            print("    Must NOT have: {}".format(case.forbidden_keywords))
        return None

    start = time.time()
    results = evaluate(suite["adapter"], suite["cases"])
    elapsed = time.time() - start

    print_eval_report(results)

    passed = sum(1 for r in results if r.passed)
    pass_rate = passed / len(results)
    target = suite["target_pass_rate"]
    status = "TARGET MET" if pass_rate >= target else "BELOW TARGET"

    print("  {}  pass rate={:.1f}%  target={:.0f}%  ({:.1f}s)\n".format(
        status, pass_rate * 100, target * 100, elapsed))
    return results


def main():
    parser = argparse.ArgumentParser(description="OpsPilot AI -- Eval Runner")
    parser.add_argument("--suite", choices=list(SUITES.keys()), help="Run a specific suite")
    parser.add_argument("--dry-run", action="store_true", help="Print cases without LLM calls")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  OpsPilot AI -- Eval Report")
    print("  APP_ENV={}".format(os.getenv("APP_ENV")))
    print("  LLM: {}".format(os.getenv("GEMINI_MODEL", "gemini/gemini-1.5-pro")))
    print("=" * 60)

    suites_to_run = [args.suite] if args.suite else list(SUITES.keys())
    all_results = []

    for key in suites_to_run:
        results = run_suite(key, dry_run=args.dry_run)
        if results:
            all_results.extend(results)

    if all_results and len(suites_to_run) > 1:
        total = len(all_results)
        passed = sum(1 for r in all_results if r.passed)
        avg_score = sum(r.score for r in all_results) / total
        print("\n" + "=" * 60)
        print("  OVERALL: {}/{} cases passed  |  avg score: {:.3f}".format(
            passed, total, avg_score))
        print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
