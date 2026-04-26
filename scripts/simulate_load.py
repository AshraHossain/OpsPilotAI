"""
simulate_load.py
================
Generates HTTP load against the sample-api service so the Infra Scaler
agent sees real CPU/memory pressure and Prometheus fires scaling alerts.

Usage:
    # Port-forward the service first (in a separate terminal):
    kubectl port-forward svc/sample-api 8080:80 -n opspilot-demo

    # Then run the load simulator:
    python scripts/simulate_load.py                  # 60s medium load
    python scripts/simulate_load.py --level high     # push CPU above 80%
    python scripts/simulate_load.py --duration 120   # run for 2 minutes
    python scripts/simulate_load.py --dry-run        # print config only

Then watch the Infra Scaler react:
    python demo_runner.py --workflow scale
"""
import argparse
import concurrent.futures
import os
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv()

TARGET_URL = os.getenv("LOAD_TARGET_URL", "http://localhost:8080")

PROFILES = {
    "low":    {"workers": 2,  "rps": 5,   "description": "Light load -- baseline metrics"},
    "medium": {"workers": 5,  "rps": 20,  "description": "Medium load -- moderate CPU pressure"},
    "high":   {"workers": 20, "rps": 100, "description": "High load -- pushes CPU above 80%"},
    "spike":  {"workers": 50, "rps": 500, "description": "Traffic spike -- triggers HPA + Scaler agent"},
}


def send_requests(worker_id, rps, duration, stop_event):
    delay = 1.0 / rps
    sent = 0
    errors = 0
    start = time.time()
    while not stop_event.is_set() and (time.time() - start) < duration:
        try:
            requests.get(TARGET_URL, timeout=2)
            sent += 1
        except Exception:
            errors += 1
        time.sleep(delay)
    return {"worker": worker_id, "sent": sent, "errors": errors}


def main():
    parser = argparse.ArgumentParser(description="OpsPilot AI -- Load Simulator")
    parser.add_argument("--level", choices=list(PROFILES.keys()), default="medium")
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds (default 60)")
    parser.add_argument("--url", default=TARGET_URL, help="Target URL")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    profile = PROFILES[args.level]

    print("\n" + "=" * 60)
    print("  OpsPilot AI -- Load Simulator")
    print("  Level   : {} -- {}".format(args.level, profile["description"]))
    print("  Target  : {}".format(args.url))
    print("  Workers : {}".format(profile["workers"]))
    print("  RPS     : {} per worker (~{} total)".format(profile["rps"], profile["rps"] * profile["workers"]))
    print("  Duration: {}s".format(args.duration))
    print("=" * 60)

    if args.dry_run:
        print("  Dry run -- no requests sent.")
        return

    # Quick connectivity check
    try:
        requests.get(args.url, timeout=3)
    except Exception as e:
        print("\n  ERROR: Cannot reach {}".format(args.url))
        print("  Run: kubectl port-forward svc/sample-api 8080:80 -n opspilot-demo")
        sys.exit(1)

    import threading
    stop_event = threading.Event()
    results = []

    print("\n  Running... (Ctrl+C to stop early)\n")
    start = time.time()

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=profile["workers"]) as ex:
            futures = [
                ex.submit(send_requests, i, profile["rps"], args.duration, stop_event)
                for i in range(profile["workers"])
            ]
            # Progress ticker
            while not all(f.done() for f in futures):
                elapsed = time.time() - start
                print("  {:.0f}s / {}s  (workers={})".format(
                    elapsed, args.duration, profile["workers"]), end="\r")
                time.sleep(2)
            results = [f.result() for f in futures]
    except KeyboardInterrupt:
        stop_event.set()
        print("\n  Stopped early.")

    elapsed = time.time() - start
    total_sent = sum(r["sent"] for r in results)
    total_errors = sum(r["errors"] for r in results)

    print("\n\n" + "=" * 60)
    print("  Load complete ({:.1f}s)".format(elapsed))
    print("  Requests sent  : {}".format(total_sent))
    print("  Errors         : {}".format(total_errors))
    print("  Effective RPS  : {:.1f}".format(total_sent / elapsed if elapsed else 0))
    print("=" * 60)
    print()
    print("  Now run the Infra Scaler to analyze the metrics:")
    print("    python demo_runner.py --workflow scale")
    print("  Or score it:")
    print("    python scripts/run_eval.py --suite scaling")
    print()


if __name__ == "__main__":
    main()
