"""
k8s_demo.py
===========
Week 3 one-command local test. Orchestrates the full Kubernetes +
Prometheus incident loop against a real minikube cluster.

Steps it runs:
  1. Verify minikube is running
  2. Apply K8s manifests (namespace, stable app, HPA)
  3. Wait for pods to become ready
  4. Apply the crashloop variant to trigger CrashLoopBackOff
  5. Wait for crash events to appear
  6. Fire the incident response workflow (real K8s tools)
  7. Show the approval gate prompt
  8. Revert to stable app

Usage:
    python scripts/k8s_demo.py                  # full flow
    python scripts/k8s_demo.py --step deploy    # just deploy stable app
    python scripts/k8s_demo.py --step crash     # apply crashloop variant
    python scripts/k8s_demo.py --step analyze   # run incident workflow only
    python scripts/k8s_demo.py --step revert    # restore stable app

Requirements:
    - minikube installed and running  (choco install minikube)
    - kubectl on PATH
    - APP_ENV=staging in .env (uses real K8s tools)
    - GOOGLE_API_KEY set in .env
"""
import argparse
import os
import subprocess
import sys
import time

from dotenv import load_dotenv
load_dotenv()

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
K8S = os.path.join(BASE, "infra", "k8s")
NAMESPACE = "opspilot-demo"


def run(cmd, check=True, capture=False):
    print("  $ " + cmd)
    result = subprocess.run(
        cmd, shell=True, check=check,
        capture_output=capture, text=True
    )
    return result


def verify_minikube():
    print("\n[1/7] Verifying minikube...")
    r = run("minikube status", check=False, capture=True)
    if "Running" not in r.stdout:
        print("  minikube is not running. Starting it now...")
        run("minikube start --driver=docker --memory=4096 --cpus=2")
    else:
        print("  minikube is running.")


def deploy_stable():
    print("\n[2/7] Deploying stable sample app...")
    run("kubectl apply -f {}".format(os.path.join(K8S, "namespace.yaml")))
    run("kubectl apply -f {}".format(os.path.join(K8S, "sample-app.yaml")))
    run("kubectl apply -f {}".format(os.path.join(K8S, "hpa.yaml")))
    print("  Waiting for pods to be ready (up to 60s)...")
    run("kubectl rollout status deployment/sample-api -n {} --timeout=60s".format(NAMESPACE))


def wait_for_ready():
    print("\n[3/7] Confirming pod health...")
    run("kubectl get pods -n {}".format(NAMESPACE))
    run("kubectl get hpa -n {}".format(NAMESPACE))


def trigger_crash():
    print("\n[4/7] Applying crashloop variant...")
    run("kubectl apply -f {}".format(os.path.join(K8S, "sample-app-crashloop.yaml")))
    print("  Waiting 30s for crash events to accumulate...")
    for i in range(6):
        time.sleep(5)
        print("  {}s...".format((i + 1) * 5))
    run("kubectl get pods -n {}".format(NAMESPACE))
    run("kubectl describe pods -n {} | grep -A5 'Events:'".format(NAMESPACE), check=False)


def run_incident_analysis():
    print("\n[5/7] Running Incident Resolver workflow (real K8s tools)...")
    os.environ["APP_ENV"] = "staging"

    if not os.getenv("GOOGLE_API_KEY"):
        print("  ERROR: GOOGLE_API_KEY not set. Cannot run LLM workflow.")
        return

    sys.path.insert(0, BASE)
    from config.context import IncidentContext
    from workflows.crew import run_incident_response

    ctx = IncidentContext(
        incident_id="k8s-demo-001",
        repo="org/api-server",
        deployment_name="sample-api",
        environment="opspilot-demo",
        alert_ids=["PodCrashLooping", "HighMemoryPressure"],
    )
    print("  Firing incident response workflow...")
    result = run_incident_response(ctx)
    print("\n" + "=" * 60)
    print("  INCIDENT RESOLVER OUTPUT:")
    print("=" * 60)
    print(result)
    return result


def show_approval_gate():
    print("\n[6/7] Testing approval gate...")
    print("  The Incident Resolver recommended a restart or rollback.")
    print("  To approve, POST to /approve (API must be running):")
    print()
    print('    curl -X POST http://localhost:8000/approve \\')
    print('      -H "Content-Type: application/json" \\')
    print('      -d \'{"incident_id": "k8s-demo-001", "approved": true, "approver": "ashraf@demo.com"}\'')
    print()
    print("  Or deny:")
    print('      -d \'{"incident_id": "k8s-demo-001", "approved": false, "approver": "ashraf@demo.com"}\'')


def revert_stable():
    print("\n[7/7] Reverting to stable app...")
    run("kubectl apply -f {}".format(os.path.join(K8S, "sample-app.yaml")))
    run("kubectl rollout status deployment/sample-api -n {} --timeout=60s".format(NAMESPACE), check=False)
    run("kubectl get pods -n {}".format(NAMESPACE))
    print("  Stable app restored.")


STEPS = {
    "deploy": deploy_stable,
    "crash": trigger_crash,
    "analyze": run_incident_analysis,
    "revert": revert_stable,
}


def main():
    parser = argparse.ArgumentParser(description="OpsPilot AI -- K8s Demo")
    parser.add_argument("--step", choices=list(STEPS.keys()),
                        help="Run a single step instead of the full flow")
    args = parser.parse_args()

    print("\n" + "#" * 60)
    print("  OpsPilot AI -- Week 3 K8s Demo")
    print("  Namespace: {}".format(NAMESPACE))
    print("#" * 60)

    if args.step:
        STEPS[args.step]()
        return

    verify_minikube()
    deploy_stable()
    wait_for_ready()
    trigger_crash()
    run_incident_analysis()
    show_approval_gate()
    input("\n  Press Enter to revert to stable app...")
    revert_stable()

    print("\n" + "#" * 60)
    print("  Week 3 demo complete.")
    print("  Next: run eval to score the Incident Resolver:")
    print("    python scripts/run_eval.py --suite incident")
    print("#" * 60 + "\n")


if __name__ == "__main__":
    main()
