"""
tests/test_eval_metrics.py
Tests for the eval framework: EvalCase scoring, pass/fail, exception handling.
"""
import pytest
from eval.metrics import EvalCase, EvalResult, evaluate


# ── EvalCase ──────────────────────────────────────────────────────────────────

class TestEvalCase:
    def test_required_fields(self):
        case = EvalCase(
            case_id="c-001",
            input={"repo": "org/repo", "pr_number": 1},
            expected_keywords=["bug", "fix"],
        )
        assert case.case_id == "c-001"
        assert "bug" in case.expected_keywords

    def test_forbidden_defaults_empty(self):
        case = EvalCase(case_id="c-002", input={}, expected_keywords=["foo"])
        assert case.forbidden_keywords == []


# ── evaluate() scoring ────────────────────────────────────────────────────────

class TestEvaluateScoring:
    def _run(self, expected, forbidden, output):
        case = EvalCase(
            case_id="x",
            input={},
            expected_keywords=expected,
            forbidden_keywords=forbidden,
        )
        return evaluate(lambda _: output, [case])[0]

    def test_all_keywords_present_passes(self):
        r = self._run(["redis", "leak", "ttl"], [], "found a redis memory leak missing ttl")
        assert r.passed is True
        assert r.score == pytest.approx(1.0)

    def test_missing_two_keywords_fails(self):
        # output only has 'redis'; 'leak' and 'ttl' are missing -> score = 1/3
        r = self._run(["redis", "leak", "ttl"], [], "found a redis issue")
        assert r.passed is False
        assert r.score == pytest.approx(1 / 3, abs=0.01)
        assert "ttl" in r.missing_keywords
        assert "leak" in r.missing_keywords

    def test_all_missing_scores_zero(self):
        r = self._run(["alpha", "beta", "gamma"], [], "completely unrelated output")
        assert r.score == pytest.approx(0.0)
        assert r.passed is False

    def test_forbidden_keyword_causes_failure(self):
        r = self._run(["redis", "leak"], ["no issues found"],
                      "redis leak detected. no issues found overall")
        assert r.passed is False
        assert "no issues found" in r.forbidden_found

    def test_forbidden_keyword_applies_penalty(self):
        # All expected present, one forbidden -> score = 1.0 - 0.2 = 0.8
        r = self._run(["redis"], ["lgtm"], "redis issue found. lgtm")
        assert r.score == pytest.approx(0.8)

    def test_case_insensitive_matching(self):
        r = self._run(["REDIS", "TTL"], [], "redis key with ttl missing")
        assert r.passed is True

    def test_empty_expected_keywords_passes_with_zero_score(self):
        # No expected keywords -> hit_rate = 0/1 = 0.0 but passed=True (nothing missing)
        r = self._run([], [], "any output whatsoever")
        assert r.passed is True
        assert r.score == pytest.approx(0.0)

    def test_raw_output_truncated_to_500(self):
        r = self._run(["x"], [], "x " + "y" * 600)
        assert len(r.raw_output) == 500


class TestEvaluateMultipleCases:
    def test_all_pass(self):
        cases = [
            EvalCase(case_id="e-001", input={}, expected_keywords=["pass"]),
            EvalCase(case_id="e-002", input={}, expected_keywords=["pass"]),
        ]
        results = evaluate(lambda _: "this will pass", cases)
        assert all(r.passed for r in results)
        assert len(results) == 2

    def test_mixed_results(self):
        cases = [
            EvalCase(case_id="m-001", input={}, expected_keywords=["alpha"]),
            EvalCase(case_id="m-002", input={}, expected_keywords=["beta"]),
        ]
        results = evaluate(lambda _: "alpha output", cases)
        passed = [r for r in results if r.passed]
        failed = [r for r in results if not r.passed]
        assert len(passed) == 1
        assert len(failed) == 1

    def test_exception_in_workflow_produces_failed_result(self):
        cases = [EvalCase(case_id="err-001", input={}, expected_keywords=["x"])]

        def boom(_):
            raise RuntimeError("agent crash")

        results = evaluate(boom, cases)
        assert len(results) == 1
        assert results[0].passed is False
        assert results[0].score == 0.0
        assert "agent crash" in results[0].error

    def test_results_length_matches_cases(self):
        cases = [EvalCase(case_id="c-" + str(i), input={}, expected_keywords=["ok"]) for i in range(7)]
        results = evaluate(lambda _: "ok", cases)
        assert len(results) == 7
