"""
LangChain-style tool wrappers for Prometheus and Alertmanager.
"""
import os
import requests
from crewai.tools import tool


def _prom_url() -> str:
    return os.getenv("PROMETHEUS_URL", "http://localhost:9090")


def _am_url() -> str:
    return os.getenv("ALERTMANAGER_URL", "http://localhost:9093")


@tool("Query Prometheus Metric")
def query_metric(promql: str) -> str:
    """
    Execute an instant PromQL query and return the result as a formatted string.
    Args:
        promql: A valid PromQL expression, e.g. 'rate(http_requests_total[5m])'.
    Returns:
        JSON result from Prometheus as a string.
    """
    url = f"{_prom_url()}/api/v1/query"
    resp = requests.get(url, params={"query": promql}, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("data", {}).get("result", [])
    if not results:
        return f"No data returned for query: {promql}"
    lines = []
    for r in results:
        metric_labels = r.get("metric", {})
        value = r.get("value", ["", ""])[1]
        lines.append(f"  {metric_labels} => {value}")
    return f"PromQL: {promql}\n" + "\n".join(lines)


@tool("Query Prometheus Range")
def query_metric_range(promql: str, start: str, end: str, step: str = "60s") -> str:
    """
    Execute a range PromQL query and return a summary of the result.
    Args:
        promql: PromQL expression.
        start: RFC3339 or Unix timestamp for range start.
        end: RFC3339 or Unix timestamp for range end.
        step: Resolution step (default '60s').
    Returns:
        Summarized metric range data.
    """
    url = f"{_prom_url()}/api/v1/query_range"
    resp = requests.get(url, params={"query": promql, "start": start, "end": end, "step": step}, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("data", {}).get("result", [])
    if not results:
        return f"No range data for query: {promql}"
    # Return first series summary only
    first = results[0]
    values = first.get("values", [])
    min_v = min(float(v[1]) for v in values)
    max_v = max(float(v[1]) for v in values)
    avg_v = sum(float(v[1]) for v in values) / len(values)
    return (
        f"PromQL range [{start} → {end}]: {promql}\n"
        f"  Series: {first.get('metric', {})}\n"
        f"  Min={min_v:.4f}  Max={max_v:.4f}  Avg={avg_v:.4f}  Points={len(values)}"
    )


@tool("Get Active Alerts")
def get_active_alerts(filter_labels: str = "") -> str:
    """
    Fetch currently firing alerts from Alertmanager.
    Args:
        filter_labels: Optional label filter string, e.g. 'severity=critical'.
    Returns:
        List of active alert names, severities, and summaries.
    """
    url = f"{_am_url()}/api/v2/alerts"
    params = {}
    if filter_labels:
        params["filter"] = filter_labels
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    alerts = resp.json()
    if not alerts:
        return "No active alerts."
    lines = []
    for a in alerts:
        labels = a.get("labels", {})
        annotations = a.get("annotations", {})
        lines.append(
            f"[{labels.get('severity', 'unknown').upper()}] {labels.get('alertname', '?')} "
            f"— {annotations.get('summary', 'no summary')}"
        )
    return "\n".join(lines)
