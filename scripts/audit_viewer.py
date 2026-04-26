"""
scripts/audit_viewer.py
=======================
CLI browser for the local audit trail (audit_trail.jsonl).
Prints a rich formatted table with filtering and tail support.

Usage:
    python scripts/audit_viewer.py                        # last 20 events
    python scripts/audit_viewer.py --limit 50             # last 50 events
    python scripts/audit_viewer.py --workflow pr_review   # filter by workflow
    python scripts/audit_viewer.py --incident inc-001     # filter by incident ID
    python scripts/audit_viewer.py --tail                 # follow new events (like tail -f)
    python scripts/audit_viewer.py --file custom.jsonl    # custom audit file
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone


# ── Colour helpers (no third-party deps) ─────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
CYAN   = "\033[36m"
DIM    = "\033[2m"

OUTCOME_COLOUR = {
    "completed":        GREEN,
    "approved":         GREEN,
    "pending_approval": YELLOW,
    "denied":           RED,
    "failed":           RED,
}

WORKFLOW_SHORT = {
    "pr_review":          "PR Review",
    "cicd_analysis":      "CI/CD",
    "scaling_analysis":   "Scaling",
    "incident_response":  "Incident",
    "approval_gate":      "Approval",
}


def colour(text: str, code: str) -> str:
    if not sys.stdout.isatty():
        return text
    return code + text + RESET


def fmt_time(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%m-%d %H:%M:%S")
    except Exception:
        return iso[:19]


def truncate(text: str, width: int) -> str:
    text = (text or "").replace("\n", " ")
    return text if len(text) <= width else text[:width - 1] + "…"


# ── Table rendering ───────────────────────────────────────────────────────────

COLS = [
    ("Time",       17),
    ("Workflow",   12),
    ("Repo",       22),
    ("Outcome",    16),
    ("Duration",    8),
    ("Summary",    55),
]


def header_line() -> str:
    parts = [BOLD + colour(label.ljust(w), CYAN) for label, w in COLS]
    return "  ".join(parts)


def separator() -> str:
    return colour("─" * 140, DIM)


def render_event(ev: dict) -> str:
    outcome = ev.get("outcome", "")
    oc = OUTCOME_COLOUR.get(outcome, "")
    dur = ev.get("duration_seconds")
    dur_str = "{:.1f}s".format(dur) if dur is not None else "—"

    cells = [
        fmt_time(ev.get("timestamp", "")).ljust(COLS[0][1]),
        WORKFLOW_SHORT.get(ev.get("workflow", ""), ev.get("workflow", ""))[:COLS[1][1]].ljust(COLS[1][1]),
        truncate(ev.get("repo", ""), COLS[2][1]).ljust(COLS[2][1]),
        colour(truncate(outcome, COLS[3][1]).ljust(COLS[3][1]), oc),
        dur_str.ljust(COLS[4][1]),
        truncate(ev.get("summary", ""), COLS[5][1]),
    ]
    return "  ".join(cells)


# ── Core reader ───────────────────────────────────────────────────────────────

def read_events(path: str, workflow: str | None, incident: str | None, limit: int) -> list:
    if not os.path.exists(path):
        return []
    events = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if workflow and ev.get("workflow") != workflow:
                continue
            if incident and ev.get("incident_id") != incident:
                continue
            events.append(ev)
    events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return events[:limit]


def tail_events(path: str, workflow: str | None, incident: str | None):
    """Follow new lines appended to the audit file (like tail -f)."""
    print(colour("Tailing {} — Ctrl+C to stop\n".format(path), DIM))
    print(separator())
    print(header_line())
    print(separator())

    if not os.path.exists(path):
        open(path, "a").close()

    with open(path, encoding="utf-8") as f:
        f.seek(0, 2)   # jump to end
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.5)
                continue
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if workflow and ev.get("workflow") != workflow:
                continue
            if incident and ev.get("incident_id") != incident:
                continue
            print(render_event(ev))


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="OpsPilot AI — Audit Trail Viewer")
    parser.add_argument("--file", default="audit_trail.jsonl", help="Audit file path")
    parser.add_argument("--limit", type=int, default=20, help="Max events to show")
    parser.add_argument("--workflow", help="Filter by workflow name (pr_review, cicd_analysis, etc.)")
    parser.add_argument("--incident", help="Filter by incident_id")
    parser.add_argument("--tail", action="store_true", help="Follow file for new events")
    args = parser.parse_args()

    if args.tail:
        try:
            tail_events(args.file, args.workflow, args.incident)
        except KeyboardInterrupt:
            print("\nStopped.")
        return

    events = read_events(args.file, args.workflow, args.incident, args.limit)

    print()
    print(colour("  OpsPilot AI — Audit Trail", BOLD))
    print(colour("  File: {}  |  Events shown: {}".format(args.file, len(events)), DIM))
    if args.workflow:
        print(colour("  Filter: workflow={}".format(args.workflow), DIM))
    if args.incident:
        print(colour("  Filter: incident={}".format(args.incident), DIM))
    print()
    print(separator())
    print(header_line())
    print(separator())

    if not events:
        print(colour("  No events found.", DIM))
    else:
        for ev in events:
            print(render_event(ev))

    print(separator())
    print()

    # Summary stats
    all_events = read_events(args.file, args.workflow, args.incident, limit=10_000)
    by_workflow: dict[str, int] = {}
    by_outcome: dict[str, int] = {}
    for ev in all_events:
        wf = ev.get("workflow", "unknown")
        oc = ev.get("outcome", "unknown")
        by_workflow[wf] = by_workflow.get(wf, 0) + 1
        by_outcome[oc] = by_outcome.get(oc, 0) + 1

    print(colour("  Total matching events: {}".format(len(all_events)), BOLD))
    for wf, count in sorted(by_workflow.items(), key=lambda x: -x[1]):
        print("    {}: {}".format(WORKFLOW_SHORT.get(wf, wf), count))
    print()
    for oc, count in sorted(by_outcome.items(), key=lambda x: -x[1]):
        c = OUTCOME_COLOUR.get(oc, "")
        print("  {} {}".format(colour(oc.ljust(20), c), count))
    print()


if __name__ == "__main__":
    main()
