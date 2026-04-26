"""
Evaluation metrics for OpsPilot AI agent outputs.
Measures detection accuracy, classification quality, and false-positive rates.
"""
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class EvalCase:
    case_id: str
    input: dict
    expected_keywords: list[str]          # keywords that MUST appear in output
    forbidden_keywords: list[str] = field(default_factory=list)  # keywords that must NOT appear


@dataclass
class EvalResult:
    case_id: str
    passed: bool
    score: float                          # 0.0 – 1.0
    missing_keywords: list[str]
    forbidden_found: list[str]
    raw_output: str
    error: str = ""                       # set if the workflow fn raised an exception


def evaluate(
    workflow_fn: Callable[[dict], str],
    cases: list[EvalCase],
) -> list[EvalResult]:
    """
    Run a list of eval cases through a workflow function and score each result.

    Args:
        workflow_fn: Function that accepts an input dict and returns an output string.
        cases: List of EvalCase objects.
    Returns:
        List of EvalResult objects with pass/fail and scores.
    """
    results = []
    for case in cases:
        try:
            output = str(workflow_fn(case.input))
        except Exception as exc:
            results.append(EvalResult(
                case_id=case.case_id,
                passed=False,
                score=0.0,
                missing_keywords=list(case.expected_keywords),
                forbidden_found=[],
                raw_output="",
                error=str(exc),
            ))
            continue

        output_lower = output.lower()
        missing = [kw for kw in case.expected_keywords if kw.lower() not in output_lower]
        forbidden = [kw for kw in case.forbidden_keywords if kw.lower() in output_lower]

        hit_rate = (len(case.expected_keywords) - len(missing)) / max(len(case.expected_keywords), 1)
        penalty = len(forbidden) * 0.2
        score = max(0.0, hit_rate - penalty)
        passed = not missing and not forbidden

        results.append(EvalResult(
            case_id=case.case_id,
            passed=passed,
            score=round(score, 3),
            missing_keywords=missing,
            forbidden_found=forbidden,
            raw_output=output[:500],
        ))

    return results


def print_eval_report(results: list[EvalResult]):
    """Print a human-readable evaluation report."""
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    avg_score = sum(r.score for r in results) / total if total else 0

    print("\n" + "=" * 60)
    print("EVAL REPORT — {}/{} passed | avg score: {:.3f}".format(passed, total, avg_score))
    print("=" * 60)
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print("\n  {}  [{}]  score={:.3f}".format(status, r.case_id, r.score))
        if r.missing_keywords:
            print("   Missing : {}".format(r.missing_keywords))
        if r.forbidden_found:
            print("   Forbidden found: {}".format(r.forbidden_found))
        if r.error:
            print("   Error: {}".format(r.error))
    print("\n" + "=" * 60 + "\n")
