# OpsPilot AI — Demo Video Script

**Duration:** ~8 minutes  
**Audience:** Engineering managers, senior DevOps engineers  
**Goal:** Show that OpsPilot AI autonomously triages incidents, reviews PRs,
and scales infrastructure — with a human approval gate before any destructive action.

---

## Scene 1 — Introduction (0:00–0:45)

**Screen:** Project README / architecture diagram

> "OpsPilot AI is a multi-agent DevOps control plane built on CrewAI and Google Gemini.
> Four specialized agents — a Code Reviewer, a CI/CD Monitor, an Infra Scaler, and an
> Incident Resolver — collaborate to handle the most common on-call scenarios automatically.
> Let me show you each one."

---

## Scene 2 — PR Code Review (0:45–2:00)

**Terminal command:**
```bash
python demo_runner.py --workflow pr
```

**Narration:**
> "We trigger the Code Reviewer against PR #42. The agent fetches the diff using
> the GitHub tool, identifies a Redis memory leak — missing `.expire()` call on a
> cache key — and flags a hardcoded TTL of 3600 seconds that should be config-driven.
> It also notices missing unit tests for the new endpoint. All of this in under 30 seconds."

**Key points to highlight in output:**
- `RISK: HIGH — Redis key with no TTL`
- `Suggested fix:` code snippet
- `Test coverage gap detected`

---

## Scene 3 — CI/CD Failure Detection (2:00–3:30)

**Terminal command:**
```bash
python demo_runner.py --workflow ci
```

**Narration:**
> "The CI/CD Monitor is triggered by a failed GitHub Actions run. It reads the
> workflow logs, pinpoints the `integration-test` step, and identifies a missing
> PostgreSQL service as the root cause — not a code bug, but a pipeline misconfiguration.
> The Incident Resolver then recommends rerunning with the service restored,
> and drafts a GitHub issue body ready to paste."

**Key points to highlight:**
- `Failing step: integration-test`
- `Root cause: missing postgres service`
- `Recommendation: rerun`

---

## Scene 4 — Infrastructure Scaling (3:30–5:00)

**Terminal command:**
```bash
python demo_runner.py --workflow scale
```

**Narration:**
> "The Infra Scaler queries Prometheus for the api-server deployment. CPU is at
> 87% — well above the HPA threshold. Memory pressure is also elevated. The agent
> recommends scaling from 3 to 6 replicas, with HIGH confidence. Crucially, it flags
> that any scale-down requires human approval before executing — this is the approval gate."

**Key points to highlight:**
- `CPU: 87%  Memory: 78%`
- `Recommendation: scale UP to 6 replicas`
- `APPROVAL REQUIRED for scale-down`

---

## Scene 5 — Full Incident Response + Approval Gate (5:00–7:00)

**Terminal commands (two windows):**
```bash
# Window 1 — API server
uvicorn api.main:app --reload

# Window 2 — trigger incident + approval
python scripts/test_approval_gate.py
```

**Narration:**
> "Here's the full loop. An Alertmanager webhook fires for PodCrashLooping.
> The Incident Resolver correlates it with pod OOMKill events and a recent CI failure.
> It produces a root-cause statement — 'Memory limit too low, OOMKilled after traffic spike' —
> and recommends restarting the pod with increased memory limits. But before any
> restart fires, the API returns `pending_approval`. We POST to `/approve`, and only
> then does the action proceed. Full audit event logged automatically."

**Key points to highlight:**
- `POST /webhook/alertmanager` → `{"status": "pending_approval"}`
- `POST /approve` → `{"status": "approved"}`
- Audit trail: `cat audit_trail.jsonl | python -m json.tool`

---

## Scene 6 — Eval Report + Closing (7:00–8:00)

**Terminal command:**
```bash
python scripts/run_eval.py --dry-run
python scripts/run_eval.py --suite cicd
```

**Narration:**
> "Every agent is measured with a precision/recall eval suite. Four suites,
> 20 cases total, each with expected keywords the output must contain and forbidden
> phrases it must not. The CI/CD suite targets 90% pass rate — the highest bar because
> false positives in pipeline analysis are costly. We hit it. You can add your own
> eval cases as your workflows evolve. OpsPilot AI — autonomous DevOps, with a human
> always in the loop for anything destructive."

---

## Filming Notes

- Use a dark terminal theme (Dracula or One Dark) for readability
- Zoom to 140% in terminal for font clarity
- Keep cursor visible during command execution
- Pause 2s after each output block before narrating
- Record at 1920×1080, export at 1080p 30fps
- Add captions for each scene title
