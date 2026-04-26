# OpsPilot AI — Eval Metrics Guide

## Overview

The eval framework scores agent output quality using keyword-based
precision/recall. Each `EvalCase` defines:

- **expected_keywords** — terms that MUST appear in the output (recall)
- **forbidden_keywords** — terms that must NOT appear (false-positive guard)

A case passes when all expected keywords are present and no forbidden
keywords appear. The score is `(keywords_found / total_expected)`.

## Suites & Targets

| Suite    | Cases | Target Pass Rate | Adapter |
|----------|-------|-----------------|---------|
| `pr`     | 5     | 80%             | `run_pr_review` |
| `cicd`   | 5     | 90%             | `run_cicd_analysis` |
| `incident` | 5   | 80%             | `run_incident_response` |
| `scaling` | 5    | 80%             | `run_scaling_analysis` |

## Running Evals

```bash
# All suites
python scripts/run_eval.py

# Single suite
python scripts/run_eval.py --suite pr
python scripts/run_eval.py --suite cicd
python scripts/run_eval.py --suite incident
python scripts/run_eval.py --suite scaling

# Dry run (print cases, no LLM calls)
python scripts/run_eval.py --dry-run
```

## Reading the Report

```
Suite: PR Code Review
Cases: 5  |  Target: 80%
──────────────────────────────────────────────────────────────────────
  PASS [pr-001] score=1.000  Redis memory leak flagged correctly
  PASS [pr-002] score=0.875  Hardcoded TTL flagged
  FAIL [pr-003] score=0.500  Missing: ['rerun', 'flaky']
  PASS [pr-004] score=1.000  Test gap detected
  PASS [pr-005] score=0.750  Type hint suggestion present
──────────────────────────────────────────────────────────────────────
  TARGET MET  pass rate=80.0%  target=80%  (34.2s)
```

- **score** — fraction of expected keywords found (1.0 = all found)
- **PASS/FAIL** — PASS if all expected keywords present AND no forbidden keywords
- **TARGET MET / BELOW TARGET** — pass rate vs. target

## Tracking Trends

Run eval after every significant prompt or tool change and record
results in a table:

| Date       | Suite    | Pass Rate | Notes |
|------------|----------|-----------|-------|
| 2025-01-10 | pr       | 80%       | Baseline |
| 2025-01-12 | pr       | 100%      | Improved diff tool context |
| 2025-01-15 | cicd     | 90%       | Baseline |
| 2025-01-15 | incident | 60%       | RCA keywords missing → fix prompt |
| 2025-01-16 | incident | 80%       | Prompt fix applied |

## Adding New Cases

Edit the relevant `eval/*_cases.py`:

```python
EvalCase(
    case_id="pr-006",
    input={"repo": "org/repo", "pr_number": 99},
    expected_keywords=["sql injection", "sanitize", "parameterized"],
    forbidden_keywords=["no issues found", "looks good"],
    description="Security: SQL injection risk should be flagged",
)
```

Keep `expected_keywords` specific (3-6 terms) and `forbidden_keywords`
targeted at the most likely false-positive phrases.
