"""
test_approval_gate.py
=====================
End-to-end test of the approval gate flow.

Steps:
  1. POST a mock Alertmanager payload to /webhook/alertmanager
     (triggers the Incident Resolver which queues a destructive action)
  2. Poll /approve/{incident_id} -- confirms action is pending
  3. POST /approve to grant approval
  4. Confirm approval status flips to approved

Usage:
    # Start the API first:
    uvicorn api.main:app --reload

    # Then in another terminal:
    python scripts/test_approval_gate.py
    python scripts/test_approval_gate.py --deny   # test denial path
    python scripts/test_approval_gate.py --url http://localhost:8000
"""
import argparse
import json
import sys
import time

import requests
from dotenv import load_dotenv
load_dotenv()

MOCK_ALERT_PAYLOAD = {
    "version": "4",
    "groupKey": "{}:{alertname='PodCrashLooping'}",
    "status": "firing",
    "receiver": "opspilot-webhook",
    "groupLabels": {"alertname": "PodCrashLooping"},
    "commonLabels": {
        "alertname": "PodCrashLooping",
        "severity": "critical",
        "deployment": "sample-api",
        "namespace": "opspilot-demo",
        "repo": "org/api-server",
        "env": "production",
    },
    "commonAnnotations": {
        "summary": "Pod is crash looping",
        "description": "sample-api has restarted 5 times in 15 minutes",
    },
    "alerts": [
        {
            "status": "firing",
            "fingerprint": "alert-crashloop-001",
            "labels": {
                "alertname": "PodCrashLooping",
                "severity": "critical",
                "deployment": "sample-api",
                "namespace": "opspilot-demo",
                "repo": "org/api-server",
                "env": "production",
            },
            "annotations": {
                "summary": "Pod sample-api is crash looping",
                "description": "Restarted 5 times in 15 minutes",
            },
        }
    ],
}


def check_api(base_url):
    try:
        r = requests.get("{}/health".format(base_url), timeout=3)
        r.raise_for_status()
        return True
    except Exception as e:
        print("  ERROR: API not reachable at {}".format(base_url))
        print("  Start it with: uvicorn api.main:app --reload")
        return False


def main():
    parser = argparse.ArgumentParser(description="OpsPilot AI -- Approval Gate E2E Test")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--deny", action="store_true", help="Test the denial path")
    parser.add_argument("--approver", default="ashraf@demo.com")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  OpsPilot AI -- Approval Gate E2E Test")
    print("  API: {}".format(args.url))
    print("  Decision: {}".format("DENY" if args.deny else "APPROVE"))
    print("=" * 60)

    if not check_api(args.url):
        sys.exit(1)

    # Step 1: Trigger the incident webhook
    print("\n[1/4] Sending Alertmanager payload to /webhook/alertmanager...")
    r = requests.post(
        "{}/webhook/alertmanager".format(args.url),
        json=MOCK_ALERT_PAYLOAD,
        timeout=120,   # agents may take time
    )
    r.raise_for_status()
    resp = r.json()
    incident_id = resp.get("incident_id", "")
    print("  Incident ID: {}".format(incident_id))
    print("  Action     : {}".format(resp.get("action")))

    if not incident_id:
        print("  ERROR: No incident_id in response.")
        sys.exit(1)

    # Step 2: Check status (should be pending or not yet approved)
    print("\n[2/4] Checking approval status...")
    r = requests.get("{}/approve/{}".format(args.url, incident_id), timeout=5)
    if r.status_code == 404:
        print("  Status: PENDING (no decision yet) -- correct behaviour")
    else:
        print("  Status: {}".format(r.json()))

    time.sleep(1)

    # Step 3: Submit decision
    decision = not args.deny
    print("\n[3/4] Submitting decision: {}...".format("APPROVE" if decision else "DENY"))
    r = requests.post(
        "{}/approve".format(args.url),
        json={
            "incident_id": incident_id,
            "approved": decision,
            "approver": args.approver,
        },
        timeout=5,
    )
    r.raise_for_status()
    print("  Response: {}".format(r.json()))

    # Step 4: Confirm
    print("\n[4/4] Confirming stored decision...")
    r = requests.get("{}/approve/{}".format(args.url, incident_id), timeout=5)
    data = r.json()
    stored = data.get("approved")
    expected = decision
    status = "PASS" if stored == expected else "FAIL"
    print("  {} -- approved={} (expected={})".format(status, stored, expected))

    print("\n" + "=" * 60)
    print("  Approval gate test {}".format("PASSED" if status == "PASS" else "FAILED"))
    print("=" * 60 + "\n")

    sys.exit(0 if status == "PASS" else 1)


if __name__ == "__main__":
    main()
