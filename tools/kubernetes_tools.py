"""
LangChain-style tool wrappers for Kubernetes operations via the official Python client.
All mutating actions (scale, restart, rollback) check the APPROVAL_GATE_ENABLED setting
and raise if a human approval is required but not yet granted.
"""
import os
from crewai.tools import tool
from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException


def _load_k8s():
    kubeconfig = os.getenv("KUBECONFIG", "")
    if kubeconfig:
        k8s_config.load_kube_config(config_file=kubeconfig)
    else:
        try:
            k8s_config.load_incluster_config()
        except k8s_config.ConfigException:
            k8s_config.load_kube_config()


def _namespace() -> str:
    return os.getenv("K8S_NAMESPACE", "default")


def _gate_check(action: str):
    if os.getenv("APPROVAL_GATE_ENABLED", "true").lower() == "true":
        raise PermissionError(
            f"Action '{action}' requires human approval. "
            "Set approved=True via the /approve endpoint before proceeding."
        )


# ── Read-only tools ───────────────────────────────────────────────────────────

@tool("Get Deployment Status")
def get_deployment_status(deployment_name: str) -> str:
    """
    Return the current status of a Kubernetes deployment.
    Args:
        deployment_name: Name of the Kubernetes deployment.
    Returns:
        Replica counts, available pods, and container image versions.
    """
    _load_k8s()
    apps_v1 = client.AppsV1Api()
    dep = apps_v1.read_namespaced_deployment(name=deployment_name, namespace=_namespace())
    spec = dep.spec
    status = dep.status
    containers = [c.image for c in spec.template.spec.containers]
    return (
        f"Deployment: {deployment_name}\n"
        f"  Replicas: desired={spec.replicas} ready={status.ready_replicas} "
        f"available={status.available_replicas}\n"
        f"  Images: {', '.join(containers)}"
    )


@tool("Get Pod Events")
def get_pod_events(deployment_name: str) -> str:
    """
    Retrieve recent Kubernetes events related to pods in a deployment.
    Args:
        deployment_name: Deployment name (used as label selector).
    Returns:
        Most recent 20 events as a formatted string.
    """
    _load_k8s()
    core_v1 = client.CoreV1Api()
    events = core_v1.list_namespaced_event(
        namespace=_namespace(),
        field_selector=f"involvedObject.name={deployment_name}",
    )
    lines = []
    for ev in sorted(events.items, key=lambda e: e.last_timestamp or "", reverse=True)[:20]:
        lines.append(
            f"[{ev.type}] {ev.reason}: {ev.message} "
            f"(count={ev.count}, last={ev.last_timestamp})"
        )
    return "\n".join(lines) or "No events found."


@tool("Get Pod Logs")
def get_pod_logs(pod_name: str, tail_lines: int = 100) -> str:
    """
    Fetch the last N lines of logs from a Kubernetes pod.
    Args:
        pod_name: Full pod name.
        tail_lines: Number of lines to return from the tail (default 100).
    Returns:
        Log text as a string.
    """
    _load_k8s()
    core_v1 = client.CoreV1Api()
    logs = core_v1.read_namespaced_pod_log(
        name=pod_name,
        namespace=_namespace(),
        tail_lines=tail_lines,
    )
    return logs or "No logs returned."


# ── Mutating tools (gated) ────────────────────────────────────────────────────

@tool("Restart Pod")
def restart_pod(deployment_name: str, approved: bool = False) -> str:
    """
    Trigger a rolling restart of all pods in a Kubernetes deployment.
    Requires approval gate to be satisfied.
    Args:
        deployment_name: Name of the deployment to restart.
        approved: Must be True (set by the approval endpoint).
    Returns:
        Confirmation string.
    """
    if not approved:
        _gate_check("restart_pod")
    _load_k8s()
    apps_v1 = client.AppsV1Api()
    from datetime import datetime, timezone
    import json
    patch = {
        "spec": {
            "template": {
                "metadata": {
                    "annotations": {
                        "kubectl.kubernetes.io/restartedAt": datetime.now(timezone.utc).isoformat()
                    }
                }
            }
        }
    }
    apps_v1.patch_namespaced_deployment(name=deployment_name, namespace=_namespace(), body=patch)
    return f"Rolling restart triggered for deployment '{deployment_name}'."


@tool("Scale Deployment")
def scale_deployment(deployment_name: str, replicas: int, approved: bool = False) -> str:
    """
    Scale a Kubernetes deployment to the specified replica count.
    Requires approval gate for scale-down operations.
    Args:
        deployment_name: Name of the deployment.
        replicas: Target replica count.
        approved: Must be True for destructive scale operations.
    Returns:
        Confirmation string.
    """
    if replicas == 0 and not approved:
        _gate_check("scale_to_zero")
    _load_k8s()
    apps_v1 = client.AppsV1Api()
    patch = {"spec": {"replicas": replicas}}
    apps_v1.patch_namespaced_deployment_scale(
        name=deployment_name, namespace=_namespace(), body=patch
    )
    return f"Deployment '{deployment_name}' scaled to {replicas} replicas."


@tool("Rollback Deployment")
def rollback_deployment(deployment_name: str, approved: bool = False) -> str:
    """
    Roll back a Kubernetes deployment to its previous revision.
    Requires human approval.
    Args:
        deployment_name: Name of the deployment.
        approved: Must be True (set by the approval endpoint).
    Returns:
        Confirmation string.
    """
    if not approved:
        _gate_check("rollback_deployment")
    _load_k8s()
    apps_v1 = client.AppsV1Api()
    patch = {"spec": {"rollbackTo": {"revision": 0}}}  # 0 = previous revision
    apps_v1.patch_namespaced_deployment(name=deployment_name, namespace=_namespace(), body=patch)
    return f"Rollback triggered for deployment '{deployment_name}'."
