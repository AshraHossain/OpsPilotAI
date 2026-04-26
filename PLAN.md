# OpsPilot AI — Project Plan
**AI DevOps Multi-Agent System**
`D:\ClaudeCode\OpsPilotAI`

> Resume framing: *"Built a multi-agent DevOps platform using CrewAI, LangChain, Kubernetes, AWS, and Prometheus to automate PR review, CI/CD failure analysis, autoscaling recommendations, and incident triage."*

---

## What This Project Is

An event-driven AI control plane with four specialized agents that each own a narrow slice of the DevOps lifecycle:

| Agent | Trigger | What it does |
|---|---|---|
| **Code Reviewer** | PR opened / updated | Reviews diff, flags risks, posts GitHub comment |
| **CI/CD Monitor** | Workflow run failed | Reads logs, identifies failing step, summarizes root cause |
| **Infra Scaler** | Metrics threshold / manual | Queries Prometheus, recommends Kubernetes replica changes |
| **Incident Resolver** | Alertmanager webhook | Correlates alerts + pod events, proposes rollback/restart, drafts RCA |

---

## Folder Map

```
D:\ClaudeCode\OpsPilotAI\
├── agents/               ← CrewAI agent definitions (one file per agent)
│   ├── code_reviewer.py
│   ├── cicd_monitor.py
│   ├── infra_scaler.py
│   └── incident_resolver.py
├── tools/                ← LangChain tool wrappers (GitHub, Prometheus, K8s)
│   ├── github_tools.py
│   ├── prometheus_tools.py
│   └── kubernetes_tools.py
├── workflows/            ← CrewAI crew + workflow entry points
│   └── crew.py
├── api/                  ← FastAPI app (webhooks, approval gate)
│   └── main.py
├── config/               ← Settings, shared context object
│   ├── settings.py
│   └── context.py
├── infra/                ← Docker, docker-compose, Helm chart
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── prometheus.yml
│   ├── alertmanager.yml
│   └── helm/
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/deployment.yaml
├── eval/                 ← Evaluation metrics (detection accuracy, F1, FP rate)
│   └── metrics.py
├── tests/                ← Pytest test suite
│   └── test_api.py
├── requirements.txt
├── .env.example
└── PLAN.md               ← this file
```

---

## Stack

| Layer | Technology |
|---|---|
| Agent orchestration | CrewAI |
| Tool / integration layer | LangChain |
| API server | FastAPI + Uvicorn |
| GitHub integration | PyGithub + webhooks |
| Kubernetes | `kubernetes` Python client |
| Metrics / alerting | Prometheus + Alertmanager |
| Cloud deployment | AWS EKS + ECR + CloudWatch |
| Containers | Docker + docker-compose |
| K8s packaging | Helm |
| LLM backend | OpenAI API (or AWS Bedrock) |
| Testing | Pytest + httpx |
| Observability | structlog + Grafana |

---

## 4-Week Build Plan

### Week 1 — Foundation (Days 1–7)
**Goal:** Everything runs locally end-to-end with mock data.

- [ ] Copy `.env.example` → `.env`, fill in `OPENAI_API_KEY` and `GITHUB_TOKEN`
- [ ] `pip install -r requirements.txt`
- [ ] Run `uvicorn api.main:app --reload` and confirm `/health` returns 200
- [ ] Write mock versions of all tools (return hardcoded strings) so agents run without real API calls
- [ ] Run `run_pr_review()` and `run_cicd_analysis()` with mock context — confirm CrewAI task loop completes
- [ ] Run `pytest tests/` — all smoke tests pass
- [ ] Commit initial structure to GitHub with a proper README

**Deliverable:** Working local dev loop with all four agents and mock tools.

---

### Week 2 — GitHub & CI/CD Integration (Days 8–14)
**Goal:** Real PR review and real pipeline failure analysis.

- [ ] Register a GitHub webhook on a test repo pointing to `localhost:8000/webhook/github` (use `ngrok` for tunnelling)
- [ ] Open a test PR → confirm `Code Reviewer` fetches diff, checks, and posts a comment
- [ ] Trigger a deliberately failing GitHub Actions workflow → confirm `CI/CD Monitor` reads logs and identifies the broken step
- [ ] Wire the `post_pr_comment` tool to write the agent's output back to the PR
- [ ] Add `create_github_issue` for CI/CD failures: auto-creates an issue with root-cause summary
- [ ] Write eval cases in `eval/metrics.py` for PR review quality (expected keywords: "risk", "test gap", etc.)
- [ ] Run eval, record baseline score

**Deliverable:** Live PR review + CI/CD failure analysis running against a real GitHub repo.

---

### Week 3 — Kubernetes & Prometheus Integration (Days 15–21)
**Goal:** Real metrics drive real scaling and incident recommendations.

- [ ] Stand up local Kubernetes cluster (minikube or kind) + deploy a sample app
- [ ] Run `docker-compose up` (from `infra/`) to start Prometheus + Alertmanager locally
- [ ] Configure Alertmanager to POST to `http://localhost:8000/webhook/alertmanager`
- [ ] Implement `query_metric` and `query_metric_range` against the real Prometheus instance
- [ ] Run `run_scaling_analysis()` with real CPU metrics → confirm scaling recommendation output
- [ ] Test `get_pod_events()` and `get_pod_logs()` against a crashlooping pod
- [ ] Test the approval gate: verify `restart_pod(approved=False)` raises `PermissionError`
- [ ] Test the full approval flow: POST `/approve` → then re-run action
- [ ] Add eval cases for incident response (expected keywords: "root cause", "rollback", "restart")

**Deliverable:** Full incident response workflow running against local K8s + Prometheus.

---

### Week 4 — Production Polish & AWS Deployment (Days 22–28)
**Goal:** Deployable, auditable, and resume-ready.

- [ ] Build Docker image: `docker build -f infra/Dockerfile -t opspilot-ai .`
- [ ] Push to AWS ECR: `aws ecr create-repository --repository-name opspilot-ai`
- [ ] Deploy to AWS EKS using Helm: `helm install opspilot infra/helm/ -f infra/helm/values.yaml`
- [ ] Add CloudWatch log group and point structlog output to it
- [ ] Set up Grafana dashboard with: active alerts, agent invocation count, approval queue depth
- [ ] Add audit trail: log every agent invocation, tool call, and approval decision to a structured log
- [ ] Run the full eval suite, document precision/recall numbers for each agent
- [ ] Record a 3-minute demo video showing: PR review → CI failure → incident → approval → resolution
- [ ] Write the GitHub README with architecture diagram, stack table, and eval results

**Deliverable:** Deployed system on AWS EKS + documented eval metrics + demo video.

---

## Architecture (Text Diagram)

```
Developer / SRE
  ↓ PRs, workflow events, approvals
┌─────────────────────────────────────────────┐
│         FastAPI + LangChain Tool Layer       │
│  /webhook/github  /webhook/alertmanager      │
│  /trigger/*       /approve                  │
└────────────┬───────────────┬────────────────┘
             ↓               ↓
     CrewAI Crew        Shared IncidentContext
     (task router)      (repo, run_id, alerts, deployment)
             ↓
  ┌──────────┬──────────┬──────────────┐
  ↓          ↓          ↓              ↓
Code      CI/CD      Infra          Incident
Reviewer  Monitor    Scaler         Resolver
  ↓          ↓          ↓              ↓
GitHub PR  GH Actions  Prometheus   K8s events
API        run logs    Alertmanager + pod logs
                           ↓
                   Kubernetes / AWS EKS
                   (scale, restart, rollback)
                           ↓
                   Human approval gate
                   (POST /approve)
```

---

## Eval Metrics to Track

| Metric | Description | Target |
|---|---|---|
| PR review recall | % of real issues flagged by agent | > 80% |
| CI failure detection | Correct failing step identified | > 90% |
| Incident classification | Alert → correct agent routed | > 85% |
| Scaling FP rate | Scale recommendations that are unnecessary | < 15% |
| Approval gate coverage | % of destructive actions gated | 100% |

---

## Resume Bullet (copy this)

> Built **OpsPilot AI**, a production-style multi-agent DevOps platform using **CrewAI**, **LangChain**, **FastAPI**, **Kubernetes**, **AWS EKS**, and **Prometheus**. Implemented specialized agents for PR code review, CI/CD failure analysis, infrastructure autoscaling, and incident triage — with human-in-the-loop approval gates for all destructive actions. Deployed on AWS EKS with Helm, evaluated agent output quality using a custom precision/recall framework.

---

## Next Steps (after Week 4)

- Add Jira/ServiceNow integration for automatic incident ticket creation
- Add historical incident memory using a vector store (Pinecone / pgvector)
- Add Grafana dashboard links embedded in incident output
- Add policy-based remediation rules (e.g. "never scale above 20 replicas in prod")
- Add a Slack bot interface for approval notifications
