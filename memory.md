# OpsPilot AI — Project Memory

## Environment & Preferences

| Setting | Value |
|---|---|
| **IDE** | Google Antigravity (default — all file edits should be compatible) |
| **LLM backend** | Google Gemini (`gemini/gemini-1.5-pro` default, `gemini/gemini-1.5-flash` for speed) |
| **API key** | `GOOGLE_API_KEY` — NEVER OpenAI |
| **Project root** | `D:\ClaudeCode\OpsPilotAI` |
| **Working folder** | Always `D:\ClaudeCode` — never the temp outputs path |

## Key Decisions Made

- **Switched from OpenAI → Google Gemini** after initial scaffold. All agents use `llm=os.getenv("GEMINI_MODEL", "gemini/gemini-1.5-pro")`.
- **Mock tool layer** (`tools/mock_tools.py`) auto-activates when `APP_ENV=development`. Switch to `APP_ENV=staging` for real GitHub/K8s/Prometheus calls.
- **Files always written via bash heredoc** (not Write tool) to avoid null-byte corruption on Windows paths.
- **Demo confirmed working** — `python demo_runner.py --workflow pr` ran successfully with Google Gemini.

## Current Build Status

| Week | Status | What was built |
|---|---|---|
| Week 1 | ✅ Done | Scaffold, 4 agents, mock tools, FastAPI, demo runner, tests |
| Week 2 | ✅ Done | GitHub Actions workflows, webhook_setup.py, ngrok_start.py, eval suites |
| Week 3 | ✅ Done | Kubernetes + Prometheus integration (local minikube + docker-compose stack) |
| Week 4 | ✅ Done | AWS EKS deployment, Helm, Grafana dashboard, audit trail |

## File Map (key files only)

```
D:\ClaudeCode\OpsPilotAI\
├── agents/               ← 4 CrewAI agents (all use GEMINI_MODEL)
│   ├── code_reviewer.py
│   ├── cicd_monitor.py
│   ├── infra_scaler.py
│   └── incident_resolver.py
├── tools/
│   ├── __init__.py       ← tool factory (real vs mock based on APP_ENV)
│   ├── mock_tools.py     ← used when APP_ENV=development
│   ├── github_tools.py   ← used when APP_ENV=staging/production
│   ├── prometheus_tools.py
│   └── kubernetes_tools.py
├── workflows/crew.py     ← CrewAI crew + 4 workflow entry points
├── api/main.py           ← FastAPI: webhooks + /approve gate
├── config/
│   ├── settings.py       ← pydantic settings (GOOGLE_API_KEY, GEMINI_MODEL, etc.)
│   └── context.py        ← IncidentContext (shared state between agents)
├── infra/
│   ├── Dockerfile
│   ├── docker-compose.yml  ← includes Prometheus + Alertmanager + Grafana
│   ├── prometheus.yml
│   └── alertmanager.yml    ← pre-wired to POST to /webhook/alertmanager
├── .github/workflows/
│   ├── ci.yml              ← normal CI pipeline
│   └── ci-fail-demo.yml    ← deliberately broken (triggers CI/CD Monitor)
├── eval/
│   ├── metrics.py              ← precision/recall evaluator
│   ├── pr_review_cases.py      ← 5 cases, target 80% pass rate
│   ├── cicd_cases.py           ← 5 cases, target 90% pass rate
│   ├── incident_cases.py       ← 5 cases, target 80% pass rate (Week 3)
│   └── scaling_cases.py        ← 5 cases, target 80% pass rate (Week 3)
├── scripts/
│   ├── ngrok_start.py          ← starts ngrok + auto-registers GitHub webhook
│   ├── webhook_setup.py        ← registers webhook via GitHub API
│   ├── run_eval.py             ← runs all 4 eval suites, prints report
│   ├── k8s_demo.py             ← 7-step K8s demo (deploy/crash/analyze/revert)
│   ├── simulate_load.py        ← HTTP load generator (low/medium/high/spike)
│   └── test_approval_gate.py   ← E2E approval gate test (POST alert → approve)
├── audit/
│   ├── __init__.py             ← exports AuditTrail, AuditEvent
│   └── trail.py                ← DynamoDB / S3 / local JSONL audit writer (Week 4)
├── docs/
│   ├── eval_metrics.md         ← precision/recall guide + trend tracking (Week 4)
│   └── demo_script.md          ← 8-scene video script (Week 4)
├── infra/
│   ├── eks/
│   │   ├── cluster.yaml        ← eksctl ClusterConfig (Week 4)
│   │   └── iam-policy.json     ← IRSA IAM policy (Week 4)
│   ├── helm/opspilot/          ← Helm chart (Week 4)
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   └── templates/          ← deployment, service, sa, hpa, ingress, _helpers
│   └── grafana/
│       ├── opspilot-dashboard.json  ← Grafana dashboard JSON (Week 4)
│       └── grafana-configmap.yaml   ← K8s ConfigMap for auto-import (Week 4)
├── demo_runner.py          ← run all 4 workflows locally with mock data
├── memory.md               ← THIS FILE
├── PLAN.md                 ← full 4-week implementation plan + checklist
├── README.md               ← GitHub-ready readme
├── requirements.txt        ← uses langchain-google-genai, NOT openai
└── .env.example            ← template: GOOGLE_API_KEY, GEMINI_MODEL, etc.
```

## .env Minimum Required

```
GOOGLE_API_KEY=AIza...
GEMINI_MODEL=gemini/gemini-1.5-pro
APP_ENV=development
```

## Commands Cheat Sheet

```bash
# Run demo (mock tools, Gemini LLM)
python demo_runner.py --workflow pr
python demo_runner.py --workflow ci
python demo_runner.py --workflow scale
python demo_runner.py --workflow incident
python demo_runner.py               # all 4

# Start API server
uvicorn api.main:app --reload

# Register GitHub webhook (needs ngrok + real GITHUB_TOKEN)
python scripts/ngrok_start.py --repo your-username/your-repo

# Run eval suites
python scripts/run_eval.py --suite pr
python scripts/run_eval.py --suite cicd
python scripts/run_eval.py

# Run tests
pytest tests/ -v

# Start full local stack (Prometheus + Alertmanager + Grafana + API)
cd infra && docker-compose up
```

## Week 3 — Completed ✅

All Week 3 files passed syntax checks. To run locally:

1. `cd infra && docker-compose up` — start Prometheus + Alertmanager + Grafana
2. `choco install minikube` then `minikube start`
3. `python scripts/k8s_demo.py --step deploy` — deploy stable app
4. `python scripts/k8s_demo.py --step crash` — trigger crashloop incident
5. `python scripts/k8s_demo.py --step analyze` — run incident agent
6. `python scripts/simulate_load.py --profile spike` — generate load for scaling
7. `python scripts/test_approval_gate.py` — test approval gate end-to-end
8. `python scripts/run_eval.py` — run all 4 eval suites

## Week 4 — Completed ✅

All Week 4 files passed syntax checks. To deploy to AWS:

```bash
# Prerequisites
brew install eksctl awscli helm
aws configure
export ECR_REPO=123456789.dkr.ecr.us-east-1.amazonaws.com/opspilot-ai

# Full deploy (first time — ~15 min for EKS cluster)
./scripts/deploy_eks.sh

# Subsequent deploys (cluster exists)
./scripts/deploy_eks.sh --skip-cluster --tag $(git rev-parse --short HEAD)

# Import Grafana dashboard
kubectl create configmap opspilot-grafana-dashboard \
  --from-file=opspilot-dashboard.json=infra/grafana/opspilot-dashboard.json \
  --namespace monitoring -o yaml --dry-run=client | kubectl apply -f -

# View audit trail (local dev)
cat audit_trail.jsonl | python -m json.tool
```

## 🎉 All 4 Weeks Complete!

The full build is done. See docs/demo_script.md for the 8-minute video walkthrough.
