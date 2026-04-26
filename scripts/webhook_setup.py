"""
webhook_setup.py
================
Registers the OpsPilot AI GitHub webhook on a repository automatically.
No manual GitHub UI required.

Usage:
    python scripts/webhook_setup.py --repo org/myrepo --url https://abc123.ngrok.io

Requirements:
    GITHUB_TOKEN and GITHUB_WEBHOOK_SECRET must be set in .env

What it does:
    1. Connects to GitHub via GITHUB_TOKEN
    2. Deletes any existing OpsPilot webhook on the repo (idempotent)
    3. Registers a new webhook for: pull_request + workflow_run events
    4. Prints a verification curl command to test the connection
"""
import argparse
import os
import sys

from dotenv import load_dotenv
from github import Github, GithubException

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Register OpsPilot AI GitHub webhook")
    parser.add_argument("--repo", required=True, help="Repo in 'owner/repo' format")
    parser.add_argument("--url", required=True, help="Public base URL (e.g. https://abc.ngrok.io)")
    parser.add_argument("--dry-run", action="store_true", help="Print config without registering")
    args = parser.parse_args()

    token = os.getenv("GITHUB_TOKEN", "")
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")

    if not token:
        print("❌ GITHUB_TOKEN not set in .env")
        sys.exit(1)
    if not secret:
        print("❌ GITHUB_WEBHOOK_SECRET not set in .env")
        sys.exit(1)

    webhook_url = args.url.rstrip("/") + "/webhook/github"
    config = {
        "url": webhook_url,
        "content_type": "json",
        "secret": secret,
        "insecure_ssl": "0",
    }
    events = ["pull_request", "workflow_run"]

    print(f"\n{'='*60}")
    print(f"  OpsPilot AI — Webhook Setup")
    print(f"{'='*60}")
    print(f"  Repo    : {args.repo}")
    print(f"  URL     : {webhook_url}")
    print(f"  Events  : {', '.join(events)}")
    print(f"  Secret  : {'*' * len(secret)}")
    print(f"{'='*60}\n")

    if args.dry_run:
        print("Dry run — no webhook registered.")
        return

    gh = Github(token)

    try:
        repo = gh.get_repo(args.repo)
    except GithubException as e:
        print(f"❌ Could not access repo '{args.repo}': {e.data.get('message', e)}")
        sys.exit(1)

    # Remove existing OpsPilot webhooks (idempotent re-runs)
    removed = 0
    for hook in repo.get_hooks():
        if "webhook/github" in hook.config.get("url", ""):
            hook.delete()
            removed += 1
    if removed:
        print(f"  Removed {removed} existing OpsPilot webhook(s).")

    # Register new webhook
    try:
        hook = repo.create_hook(
            name="web",
            config=config,
            events=events,
            active=True,
        )
        print(f"  ✅ Webhook registered (id={hook.id})")
        print(f"     {webhook_url}")
    except GithubException as e:
        print(f"❌ Failed to create webhook: {e.data.get('message', e)}")
        sys.exit(1)

    print(f"\n  Test it:")
    print(f"  curl -X POST {webhook_url} \\")
    print(f"    -H 'Content-Type: application/json' \\")
    print(f"    -d '{{\"action\":\"ignored\",\"repository\":{{\"full_name\":\"{args.repo}\"}}}}'")
    print()
    print("  Next: open a PR or trigger the 'CI Pipeline (Fail Demo)' workflow.")
    print()


if __name__ == "__main__":
    main()
