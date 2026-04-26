# OpsPilot AI — Architecture

## System Overview

OpsPilot AI is a multi-agent DevOps control plane. External events (GitHub webhooks, Alertmanager alerts) arrive at a FastAPI gateway, which routes them to the appropriate CrewAI agent workflow. All destructive actions are gated behind a human approval step before execution. Every workflow decision is written to an immutable audit trail.

---

## Component Diagram

```mermaid
graph TD
    subgraph External["External Events"]
        GH["GitHub\n(PR / workflow_run)"]
        AM["Alertmanager\n(PodCrashLooping, OOM, CPU)"]
        OPS["Operator\n(/trigger/scale-analysis)"]
    end

    subgraph Gateway["FastAPI Gateway  (api/main.py)"]
        WH_GH["/webhook/github"]
        WH_AM["/webhook/alertmanager"]
        WH_SC["/trigger/scale-analysis"]
        APPROVE["/approve  (POST/GET)"]
        METRICS["/metrics  (Prometheus)"]
        AUDIT_EP["/audit  (GET)"]
    end

    subgraph Agents["CrewAI Agents  (agents/)"]
        CR["Code Reviewer\n(PR diffs, CI status)"]
        CI["CI/CD Monitor\n(workflow logs, root cause)"]
        IS["Infra Scaler\n(Prometheus metrics, HPA)"]
        IR["Incident Resolver\n(RCA, remediation, RCA doc)"]
    end

    subgraph Tools["Tool Layer  (tools/)"]
        GT["GitHub Tools\nget_pr_diff\nget_workflow_logs\ncreate_issue"]
        KT["Kubernetes Tools\nget_pod_events\nget_pod_logs\nrestart_deployment"]
        PT["Prometheus Tools\nquery_metric\nget_active_alerts"]
    end

    subgraph Safety["Safety Layer"]
        AG["Approval Gate\n_approval_store"]
        AT["Audit Trail\naudit/trail.py\n(DynamoDB / S3 / local)"]
    end

    subgraph Infra["Infrastructure"]
        EKS["AWS EKS\n(opspilot-cluster)"]
        ECR["Amazon ECR\n(opspilot-ai image)"]
        DDB["DynamoDB\n(opspilot-audit-trail)"]
        GRAF["Grafana\n(opspilot-dashboard)"]
        PROM["Prometheus\n(scrapes /metrics)"]
    end

    GH -->|webhook POST| WH_GH
    AM -->|alert POST| WH_AM
    OPS -->|manual trigger| WH_SC

    WH_GH -->|pr_review| CR
    WH_GH -->|cicd_analysis| CI
    WH_AM -->|incident_response| IR
    WH_SC -->|scaling_analysis| IS

    CR --> GT
    CI --> GT
    IS --> PT
    IS --> KT
    IR --> PT
    IR --> KT
    IR --> GT

    KT -->|destructive action| AG
    AG -->|approved=True| KT
    APPROVE --> AG

    CR --> AT
    CI --> AT
    IS --> AT
    IR --> AT

    AT -->|prod| DDB
    AT -->|local| AUDIT_EP

    PROM -->|scrape| METRICS
    GRAF -->|query| PROM

    EKS --- Agents
    ECR -->|image pull| EKS
```

---

## Data Flow — PR Review

```mermaid
sequenceDiagram
    participant GH as GitHub
    participant API as FastAPI
    participant CR as Code Reviewer
    participant GT as GitHub Tools
    participant AT as Audit Trail

    GH->>API: POST /webhook/github (pull_request.opened)
    API->>CR: run_pr_review(ctx)
    CR->>GT: get_pr_diff(repo, pr_number)
    GT-->>CR: diff text
    CR->>GT: get_ci_status(repo, pr_number)
    GT-->>CR: CI check results
    CR-->>API: markdown review summary
    API->>AT: log(workflow=pr_review, outcome=completed)
    API-->>GH: 200 {incident_id, result}
```

---

## Data Flow — Full Incident Response with Approval Gate

```mermaid
sequenceDiagram
    participant AM as Alertmanager
    participant API as FastAPI
    participant CI as CI/CD Monitor
    participant IS as Infra Scaler
    participant IR as Incident Resolver
    participant KT as K8s Tools
    participant OPS as Operator
    participant AT as Audit Trail

    AM->>API: POST /webhook/alertmanager (PodCrashLooping)
    API->>CI: monitor_task (workflow logs)
    CI-->>IR: failure summary
    API->>IS: scaler_task (Prometheus metrics)
    IS-->>IR: metrics summary
    IR->>KT: get_pod_events(deployment)
    KT-->>IR: OOMKilled events
    IR-->>API: RCA + recommended restart
    API->>AT: log(outcome=pending_approval)
    API-->>AM: {status: pending_approval}

    OPS->>API: POST /approve {incident_id, approved: true}
    API->>KT: restart_deployment(deployment)
    KT-->>API: restarted
    API->>AT: log(outcome=approved, approver=ops@)
```

---

## Component Table

| Component | File(s) | Purpose |
|-----------|---------|---------|
| FastAPI gateway | `api/main.py` | Webhook ingestion, approval gate, `/metrics`, `/audit` |
| Code Reviewer | `agents/code_reviewer.py` | PR diff analysis, test gap detection |
| CI/CD Monitor | `agents/cicd_monitor.py` | Pipeline log parsing, root-cause identification |
| Infra Scaler | `agents/infra_scaler.py` | Prometheus-driven replica recommendations |
| Incident Resolver | `agents/incident_resolver.py` | RCA correlation, remediation + draft docs |
| Crew orchestrator | `workflows/crew.py` | 4 workflow entry points, audit trail wiring |
| Tool factory | `tools/__init__.py` | Selects real vs. mock tools via `APP_ENV` |
| Mock tools | `tools/mock_tools.py` | Realistic hardcoded responses for local dev |
| Real tools | `tools/github_tools.py` etc. | Live GitHub / K8s / Prometheus calls |
| Approval gate | `api/main.py` `_approval_store` | Blocks destructive K8s actions until approved |
| Audit trail | `audit/trail.py` | Immutable event log — DynamoDB/S3/local |
| Eval framework | `eval/metrics.py` | Keyword precision/recall scorer, 20 test cases |
| EKS cluster | `infra/eks/cluster.yaml` | eksctl-managed 2–6 node managed node group |
| Helm chart | `infra/helm/opspilot/` | Deployment, HPA, Ingress, ServiceAccount (IRSA) |
| Grafana dashboard | `infra/grafana/` | 9-panel ops dashboard, auto-imported via ConfigMap |
| CI/CD pipeline | `.github/workflows/ci.yml` | lint → test → ECR push → helm deploy |

---

## Environment Modes

| `APP_ENV` | Tools used | LLM | Audit backend |
|-----------|-----------|-----|---------------|
| `development` | `mock_tools.py` | Gemini (real) | `local` (JSONL file) |
| `staging` | real GitHub/K8s/Prometheus | Gemini (real) | `s3` |
| `production` | real GitHub/K8s/Prometheus | Gemini (real) | `dynamodb` |

---

## Secret Management

**Local dev:** `.env` file (never committed — in `.gitignore`)

**EKS production:** AWS Secrets Manager via IRSA. The `opspilot-sa` ServiceAccount has IAM permissions scoped to `secretsmanager:GetSecretValue` for paths under `opspilot/*`. Secrets are injected as env vars from the `opspilot-secrets` K8s Secret (created by `deploy_eks.sh` from `.env`).

For fully automated secret rotation, deploy the [External Secrets Operator](https://external-secrets.io) and apply `infra/eks/external-secrets.yaml`.
