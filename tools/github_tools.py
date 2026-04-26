"""
LangChain-style tool wrappers for GitHub API operations.
Each function is decorated so CrewAI can register it as a callable tool.
"""
import os
from crewai.tools import tool
from github import Github, GithubException


def _gh_client() -> Github:
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        raise EnvironmentError("GITHUB_TOKEN is not set.")
    return Github(token)


# ── PR tools ─────────────────────────────────────────────────────────────────

@tool("Get PR Diff")
def get_pr_diff(repo_full_name: str, pr_number: int) -> str:
    """
    Fetch the unified diff for a GitHub pull request.
    Args:
        repo_full_name: Repository in 'owner/repo' format.
        pr_number: Pull request number.
    Returns:
        Unified diff as a string (truncated to 8 000 chars to stay within context).
    """
    gh = _gh_client()
    repo = gh.get_repo(repo_full_name)
    pr = repo.get_pull(pr_number)
    files = pr.get_files()
    diff_parts = []
    for f in files:
        diff_parts.append(f"--- {f.filename} (+{f.additions} / -{f.deletions})\n{f.patch or ''}")
    return "\n\n".join(diff_parts)[:8000]


@tool("Get PR Checks")
def get_pr_checks(repo_full_name: str, pr_number: int) -> str:
    """
    Return the CI check results for the HEAD commit of a pull request.
    Args:
        repo_full_name: Repository in 'owner/repo' format.
        pr_number: Pull request number.
    Returns:
        Check name, status, and conclusion for every check run.
    """
    gh = _gh_client()
    repo = gh.get_repo(repo_full_name)
    pr = repo.get_pull(pr_number)
    commit = repo.get_commit(pr.head.sha)
    runs = commit.get_check_runs()
    lines = []
    for run in runs:
        lines.append(f"{run.name}: status={run.status} conclusion={run.conclusion}")
    return "\n".join(lines) or "No check runs found."


@tool("Post PR Comment")
def post_pr_comment(repo_full_name: str, pr_number: int, body: str) -> str:
    """
    Post a review comment on a GitHub pull request.
    Args:
        repo_full_name: Repository in 'owner/repo' format.
        pr_number: Pull request number.
        body: Markdown text to post as a comment.
    Returns:
        Confirmation string with the comment URL.
    """
    gh = _gh_client()
    repo = gh.get_repo(repo_full_name)
    pr = repo.get_pull(pr_number)
    comment = pr.create_issue_comment(body)
    return f"Comment posted: {comment.html_url}"


# ── Workflow / CI tools ───────────────────────────────────────────────────────

@tool("Get Workflow Run")
def get_workflow_run(repo_full_name: str, run_id: int) -> str:
    """
    Fetch metadata for a specific GitHub Actions workflow run.
    Args:
        repo_full_name: Repository in 'owner/repo' format.
        run_id: The workflow run ID.
    Returns:
        Run name, status, conclusion, and per-job summary.
    """
    gh = _gh_client()
    repo = gh.get_repo(repo_full_name)
    run = repo.get_workflow_run(run_id)
    jobs = run.jobs()
    job_lines = []
    for job in jobs:
        steps = ", ".join(
            f"{s.name}({s.conclusion})" for s in job.steps if s.conclusion != "success"
        )
        job_lines.append(f"  Job '{job.name}': {job.conclusion} — failed steps: [{steps}]")
    return (
        f"Run #{run_id}: {run.name}\n"
        f"Status: {run.status} | Conclusion: {run.conclusion}\n"
        f"Triggered by: {run.event} on {run.head_branch}\n"
        + "\n".join(job_lines)
    )


@tool("Get Workflow Logs")
def get_workflow_logs(repo_full_name: str, run_id: int) -> str:
    """
    Download and return the log text for a failed GitHub Actions workflow run.
    Truncated to 10 000 characters.
    Args:
        repo_full_name: Repository in 'owner/repo' format.
        run_id: The workflow run ID.
    Returns:
        Raw log text (truncated).
    """
    import requests, zipfile, io

    gh = _gh_client()
    repo = gh.get_repo(repo_full_name)
    run = repo.get_workflow_run(run_id)
    logs_url = run.logs_url
    headers = {"Authorization": f"Bearer {os.getenv('GITHUB_TOKEN', '')}"}
    resp = requests.get(logs_url, headers=headers, timeout=30)
    resp.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(resp.content))
    text_parts = []
    for name in z.namelist():
        text_parts.append(f"=== {name} ===\n{z.read(name).decode('utf-8', errors='replace')}")
    return "\n\n".join(text_parts)[:10000]


# ── Issue tools ───────────────────────────────────────────────────────────────

@tool("Create GitHub Issue")
def create_github_issue(repo_full_name: str, title: str, body: str, labels: list[str] = None) -> str:
    """
    Create a GitHub issue to track an incident or follow-up action.
    Args:
        repo_full_name: Repository in 'owner/repo' format.
        title: Issue title.
        body: Issue body (markdown).
        labels: Optional list of label names.
    Returns:
        The URL of the newly created issue.
    """
    gh = _gh_client()
    repo = gh.get_repo(repo_full_name)
    issue = repo.create_issue(title=title, body=body, labels=labels or [])
    return f"Issue created: {issue.html_url}"
