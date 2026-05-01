# OpsPilot AI

[![CI](https://github.com/AshraHossain/OpsPilotAI/actions/workflows/ci.yml/badge.svg)](https://github.com/AshraHossain/OpsPilotAI/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![LLM: Ollama](https://img.shields.io/badge/LLM-Ollama%20gemma4%3A26b-orange.svg)](https://ollama.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A **multi-agent DevOps control plane** built on [CrewAI](https://github.com/crewai/crewai). Four specialized AI agents collaborate to handle the most common on-call scenarios — automatically, with a human approval gate before any destructive action.

Runs **100% locally by default** using [Ollama](https://ollama.com) (gemma4:26b) — no API key or cloud account required. Swap to any cloud model (Claude, Gemini, OpenRouter, Moonshot) via a single env variable.

---

## What It Does

| Workflow | Trigger | Agents | Output |
|----------|---------|--------|--------|
| **PR Code Review** | GitHub `pull_request` webhook | Code Reviewer | Markdown review: risk flags, test gaps, suggested fixes |
| **CI/CD Failure Analysis** | GitHub `workflow_run` webhook | CI/CD Monitor + Incident Resolver | Root-cause summary + draft GitHub issue |
| **Infra Scaling Analysis** | Alertmanager / manual POST | Infra Scaler | Replica recommendation + Prometheus evidence |
| **Full Incident Response** | Alertmanager alert group | CI/CD Monitor + Infra Scaler + Incident Resolver | RCA + remediation plan + approval gate |

---

## Architecture

```
GitHub / Alertmanager
        │
        ▼
  FastAPI Gateway  ──── /metrics (Prometheus)
  (api/main.py)    ──── /audit   (audit trail)
        │
        ▼
  CrewAI Crew  ──► Code Reviewer   ──► GitHub Tools
               ──► CI/CD Monitor   ──► GitHub Tools
               ──► Infra Scaler    ──► Prometheus + K8s Tools
               ──► Incident Resolver ► K8s + Prometheus + GitHub Tools
                          │
                          ▼
               Approval Gate  ──►  Audit Trail
               (human required        (DynamoDB / S3 / local)
                for destructive
                K8s actions)
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for full Mermaid diagrams and sequence flows.

---

## Quick Start — Local Dev (no cloud required)

### 1. Prerequisites

- [Ollama](https://ollama.com) installed and running
- Python 3.12+

```bash
# Pull the default model
ollama pull gemma4:26b

git clone https://github.com/AshraHossain/OpsPilotAI
cd OpsPilotAI
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# For local dev, no changes needed — Ollama runs by default:
#   AGENT_MODEL=ollama/gemma4:26b
#   OLLAMA_API_BASE=http://localhost:11434
```

That's it. No API key required for local development.

### 3. Run the demo

```bash
python demo_runner.py              # all 4 workflows with mock data
python demo_runner.py --workflow pr
python demo_runner.py --workflow ci
python demo_runner.py --workflow scale
python demo_runner.py --workflow incident
```

### 4. Start the API server

```bash
uvicorn api.main:app --reload
# http://localhost:8000/docs     — Swagger UI
# http://localhost:8000/metrics  — Prometheus metrics
# http://localhost:8000/audit    — Audit trail
```

---

## Switching LLM Providers

Set `AGENT_MODEL` in your `.env` to swap models with no code changes:

| Provider | Example value |
|----------|--------------|
| **Ollama (local, default)** | `ollama/gemma4:26b` |
| Google Gemini | `gemini/gemini-2.5-flash` |
| Claude via OpenRouter | `openrouter/anthropic/claude-3.5-sonnet` |
| Kimi / Moonshot | `moonshot/moonshot-v1-32k` |

Cloud providers also need their respective API key set (see `.env.example`).

---

## Run Evals

```bash
python scripts/run_eval.py              # all 4 suites
python scripts/run_eval.py --suite pr   # PR review (target 80%)
python scripts/run_eval.py --suite cicd # CI/CD monitor (target 90%)
python scripts/run_eval.py --dry-run    # print cases, no LLM calls
```

Current targets:

| Suite | Cases | Target |
|-------|-------|--------|
| PR Review | 5 | ≥ 80% |
| CI/CD Detection | 5 | ≥ 90% |
| Incident Resolver | 5 | ≥ 80% |
| Infra Scaler | 5 | ≥ 80% |

---

## Run Tests

```bash
pytest tests/ -v
```

---

## Connect to Real APIs (staging)

Set in `.env`:

```bash
APP_ENV=staging
GITHUB_TOKEN=ghp_...
GITHUB_WEBHOOK_SECRET=your-secret
```

Register a GitHub webhook (requires ngrok for local testing):

```bash
python scripts/ngrok_start.py --repo your-org/your-repo
```

---

## Kubernetes + Prometheus (local)

```bash
# Start the full observability stack
cd infra && docker-compose up

# Install minikube and deploy a crashlooping app
choco install minikube          # Windows; brew install minikube on Mac
minikube start
python scripts/k8s_demo.py --step deploy
python scripts/k8s_demo.py --step crash
python scripts/k8s_demo.py --step analyze

# Generate load to trigger scaling alerts
python scripts/simulate_load.py --profile spike --target http://localhost:8000

# Test the approval gate end-to-end
python scripts/test_approval_gate.py
```

---

## Deploy to AWS EKS

```bash
# Prerequisites: aws configure, eksctl, helm, docker installed
export ECR_REPO=123456789.dkr.ecr.us-east-1.amazonaws.com/opspilot-ai

# First deploy (~15 min for cluster creation)
./scripts/deploy_eks.sh

# Subsequent deploys
./scripts/deploy_eks.sh --skip-cluster --tag $(git rev-parse --short HEAD)
```

For secret management via AWS Secrets Manager:

```bash
kubectl apply -f infra/eks/external-secrets.yaml
```

---

## View the Audit Trail

```bash
# Local JSONL viewer
python scripts/audit_viewer.py
python scripts/audit_viewer.py --workflow incident_response
python scripts/audit_viewer.py --tail   # live follow
```

---

## Project Structure

```
OpsPilotAI/
├── agents/           ← 4 CrewAI agents (all use AGENT_MODEL)
├── tools/            ← real / mock tool factory (APP_ENV switching)
├── workflows/crew.py ← 4 workflow entry points + audit trail wiring
├── api/main.py       ← FastAPI: webhooks, /approve, /metrics, /audit
├── audit/trail.py    ← Immutable event log (DynamoDB / S3 / local)
├── config/settings.py← Pydantic settings — env-driven, Ollama default
├── eval/             ← 20 eval cases across 4 suites
├── scripts/          ← demo, k8s, load, approval gate, audit viewer
├── infra/
│   ├── Dockerfile
│   ├── docker-compose.yml   ← Prometheus + Alertmanager + Grafana
│   ├── eks/                 ← eksctl cluster + IAM policy
│   ├── helm/opspilot/       ← full Helm chart
│   ├── grafana/             ← 9-panel dashboard JSON
│   └── k8s/                 ← K8s manifests (stable, crashloop, OOM, HPA)
├── docs/
│   ├── ARCHITECTURE.md
│   ├── eval_metrics.md
│   └── demo_script.md
├── tests/
│   ├── test_audit.py        ← 12 audit trail tests
│   ├── test_eval_metrics.py ← 14 eval framework tests
│   └── test_api.py          ← API endpoint tests
└── .github/workflows/
    ├── ci.yml               ← lint → test → ECR push → helm deploy
    └── ci-fail-demo.yml     ← deliberately broken (triggers CI/CD Monitor)
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AGENT_MODEL` | No | `ollama/gemma4:26b` | LLM model string (any LiteLLM-compatible) |
| `OLLAMA_API_BASE` | No | `http://localhost:11434` | Ollama server URL |
| `OPENROUTER_API_KEY` | Cloud only | — | OpenRouter API key |
| `MOONSHOT_API_KEY` | Cloud only | — | Kimi / Moonshot AI key |
| `GOOGLE_API_KEY` | Cloud only | — | Google Gemini key |
| `APP_ENV` | No | `development` | `development` / `staging` / `production` |
| `GITHUB_TOKEN` | Staging+ | — | GitHub PAT for real tool calls |
| `GITHUB_WEBHOOK_SECRET` | Staging+ | — | Webhook HMAC secret |
| `AUDIT_BACKEND` | No | `local` | `local` / `s3` / `dynamodb` |
| `AUDIT_TABLE` | Prod | `opspilot-audit-trail` | DynamoDB table name |
| `AUDIT_S3_BUCKET` | Staging+ | `opspilot-audit-logs` | S3 bucket for audit logs |

---

## Tech Stack

- **Agent framework:** [CrewAI](https://github.com/crewai/crewai)
- **LLM (default):** [Ollama](https://ollama.com) running gemma4:26b locally — no API key
- **LLM (cloud options):** Google Gemini, Claude via OpenRouter, Kimi/Moonshot
- **API:** FastAPI + uvicorn
- **Metrics:** prometheus-client
- **K8s:** kubernetes Python SDK + minikube (local) / EKS (prod)
- **CI/CD:** GitHub Actions → Amazon ECR → Helm on EKS
- **Observability:** Prometheus + Grafana + Alertmanager
- **Audit:** DynamoDB (prod) / S3 (staging) / JSONL (local)
