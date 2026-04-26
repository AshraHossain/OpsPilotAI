#!/usr/bin/env bash
# scripts/deploy_eks.sh
# ----------------------
# One-command EKS deployment for OpsPilot AI.
# Wraps eksctl + helm with pre-flight checks.
#
# Usage:
#   chmod +x scripts/deploy_eks.sh
#   ./scripts/deploy_eks.sh                      # full deploy
#   ./scripts/deploy_eks.sh --dry-run            # print commands only
#   ./scripts/deploy_eks.sh --skip-cluster       # skip eksctl (cluster already exists)
#   ./scripts/deploy_eks.sh --tag v1.2.3         # deploy a specific image tag

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
CLUSTER_CONFIG="infra/eks/cluster.yaml"
HELM_CHART="infra/helm/opspilot"
NAMESPACE="opspilot"
RELEASE_NAME="opspilot"
ECR_REPO="${ECR_REPO:-}"          # set in env or .env
AWS_REGION="${AWS_REGION:-us-east-1}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
DRY_RUN=false
SKIP_CLUSTER=false

# ── Parse args ────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run)      DRY_RUN=true; shift ;;
    --skip-cluster) SKIP_CLUSTER=true; shift ;;
    --tag)          IMAGE_TAG="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

run() {
  echo "  >> $*"
  if [[ "$DRY_RUN" == "false" ]]; then
    "$@"
  fi
}

# ── Pre-flight checks ─────────────────────────────────────────────────────────
echo ""
echo "=============================================="
echo "  OpsPilot AI — EKS Deploy"
echo "  Region : $AWS_REGION"
echo "  Tag    : $IMAGE_TAG"
echo "  DryRun : $DRY_RUN"
echo "=============================================="
echo ""

for cmd in aws eksctl helm kubectl docker; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "ERROR: '$cmd' not found. Install it and retry."
    exit 1
  fi
done

if [[ -z "$ECR_REPO" ]]; then
  echo "ERROR: ECR_REPO is not set."
  echo "  export ECR_REPO=123456789.dkr.ecr.us-east-1.amazonaws.com/opspilot-ai"
  exit 1
fi

# ── Step 1: Build & push Docker image ────────────────────────────────────────
echo "Step 1/5 — Build & push Docker image"
run aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_REPO"

run docker build -t "$ECR_REPO:$IMAGE_TAG" -f infra/Dockerfile .
run docker push "$ECR_REPO:$IMAGE_TAG"
echo ""

# ── Step 2: Create EKS cluster (if needed) ───────────────────────────────────
if [[ "$SKIP_CLUSTER" == "false" ]]; then
  echo "Step 2/5 — Create EKS cluster (this takes ~15 min)"
  run eksctl create cluster -f "$CLUSTER_CONFIG"
else
  echo "Step 2/5 — Skipping cluster creation (--skip-cluster)"
  run eksctl utils write-kubeconfig --cluster opspilot-cluster --region "$AWS_REGION"
fi
echo ""

# ── Step 3: Create namespace + secrets ───────────────────────────────────────
echo "Step 3/5 — Namespace + secrets"
run kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
run kubectl create secret generic opspilot-secrets \
  --namespace "$NAMESPACE" \
  --from-env-file=.env \
  --dry-run=client -o yaml | kubectl apply -f -
echo ""

# ── Step 4: Apply K8s Prometheus alert rules ──────────────────────────────────
echo "Step 4/5 — Prometheus rules"
run kubectl apply -f infra/k8s/prometheus-rules.yaml
echo ""

# ── Step 5: Helm upgrade --install ───────────────────────────────────────────
echo "Step 5/5 — Helm deploy"
run helm upgrade --install "$RELEASE_NAME" "$HELM_CHART" \
  --namespace "$NAMESPACE" \
  --create-namespace \
  --set image.repository="$ECR_REPO" \
  --set image.tag="$IMAGE_TAG" \
  --wait \
  --timeout 5m

echo ""
echo "=============================================="
echo "  Deploy complete!"
echo "  kubectl get pods -n $NAMESPACE"
echo "  kubectl get ingress -n $NAMESPACE"
echo "=============================================="
