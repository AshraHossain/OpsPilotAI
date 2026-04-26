"""
Tool factory — automatically selects real or mock tools based on APP_ENV.

Usage (in agent definitions):
    from tools import get_tools

    tools = get_tools("github")       # returns list of GitHub tools
    tools = get_tools("prometheus")   # returns list of Prometheus tools
    tools = get_tools("kubernetes")   # returns list of K8s tools
    tools = get_tools("all")          # returns all tools

In development (APP_ENV=development), mock tools are used automatically.
In staging/production, real tools are used.
"""
import os
from typing import Literal

ToolGroup = Literal["github", "prometheus", "kubernetes", "all"]


def _is_dev() -> bool:
    return os.getenv("APP_ENV", "development").lower() == "development"


def get_tools(group: ToolGroup = "all") -> list:
    if _is_dev():
        from tools.mock_tools import (
            mock_get_pr_diff as get_pr_diff,
            mock_get_pr_checks as get_pr_checks,
            mock_post_pr_comment as post_pr_comment,
            mock_get_workflow_run as get_workflow_run,
            mock_get_workflow_logs as get_workflow_logs,
            mock_create_github_issue as create_github_issue,
            mock_query_metric as query_metric,
            mock_query_metric_range as query_metric_range,
            mock_get_active_alerts as get_active_alerts,
            mock_get_deployment_status as get_deployment_status,
            mock_get_pod_events as get_pod_events,
            mock_get_pod_logs as get_pod_logs,
            mock_restart_pod as restart_pod,
            mock_scale_deployment as scale_deployment,
            mock_rollback_deployment as rollback_deployment,
        )
    else:
        from tools.github_tools import (
            get_pr_diff, get_pr_checks, post_pr_comment,
            get_workflow_run, get_workflow_logs, create_github_issue,
        )
        from tools.prometheus_tools import (
            query_metric, query_metric_range, get_active_alerts,
        )
        from tools.kubernetes_tools import (
            get_deployment_status, get_pod_events, get_pod_logs,
            restart_pod, scale_deployment, rollback_deployment,
        )

    github_tools = [get_pr_diff, get_pr_checks, post_pr_comment,
                    get_workflow_run, get_workflow_logs, create_github_issue]
    prometheus_tools = [query_metric, query_metric_range, get_active_alerts]
    kubernetes_tools = [get_deployment_status, get_pod_events, get_pod_logs,
                        restart_pod, scale_deployment, rollback_deployment]

    if group == "github":
        return github_tools
    elif group == "prometheus":
        return prometheus_tools
    elif group == "kubernetes":
        return kubernetes_tools
    else:
        return github_tools + prometheus_tools + kubernetes_tools
