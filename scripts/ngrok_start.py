"""
ngrok_start.py
==============
Starts ngrok on port 8000 and automatically runs webhook_setup.py
with the public URL so the GitHub webhook is registered in one command.

Usage:
    # Step 1 — start the API server in one terminal:
    uvicorn api.main:app --reload

    # Step 2 — start ngrok + register webhook in another terminal:
    python scripts/ngrok_start.py --repo org/myrepo

Requirements:
    - ngrok installed and on PATH  (https://ngrok.com/download)
    - NGROK_AUTHTOKEN set in .env  (free account at ngrok.com)
    - GITHUB_TOKEN + GITHUB_WEBHOOK_SECRET set in .env
"""
import argparse
import os
import subprocess
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv()

NGROK_API = "http://localhost:4040/api/tunnels"
PORT = 8000


def get_public_url(retries: int = 10, delay: float = 1.0) -> str:
    """Poll the ngrok local API until a tunnel appears."""
    for i in range(retries):
        try:
            resp = requests.get(NGROK_API, timeout=3)
            tunnels = resp.json().get("tunnels", [])
            for t in tunnels:
                if t.get("proto") == "https":
                    return t["public_url"]
        except Exception:
            pass
        time.sleep(delay)
    raise TimeoutError("ngrok tunnel did not appear within the timeout.")


def main():
    parser = argparse.ArgumentParser(description="Start ngrok and register GitHub webhook")
    parser.add_argument("--repo", required=True, help="Repo in 'owner/repo' format")
    parser.add_argument("--port", type=int, default=PORT, help=f"Local port (default {PORT})")
    args = parser.parse_args()

    authtoken = os.getenv("NGROK_AUTHTOKEN", "")
    if not authtoken:
        print("⚠️  NGROK_AUTHTOKEN not set — ngrok may prompt for login.")

    print(f"\n  Starting ngrok → localhost:{args.port} ...")

    # Start ngrok as a background process
    ngrok_cmd = ["ngrok", "http", str(args.port), "--log=stdout"]
    if authtoken:
        ngrok_cmd += ["--authtoken", authtoken]

    proc = subprocess.Popen(
        ngrok_cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        public_url = get_public_url()
    except TimeoutError:
        print("❌ Could not get ngrok URL. Is ngrok installed? Run: choco install ngrok")
        proc.terminate()
        sys.exit(1)

    print(f"  ✅ ngrok tunnel active: {public_url}")
    print(f"     Webhook URL: {public_url}/webhook/github\n")

    # Register the webhook automatically
    setup_cmd = [
        sys.executable,
        "scripts/webhook_setup.py",
        "--repo", args.repo,
        "--url", public_url,
    ]
    result = subprocess.run(setup_cmd)
    if result.returncode != 0:
        proc.terminate()
        sys.exit(result.returncode)

    print("  Press Ctrl+C to stop ngrok.\n")
    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\n  Stopping ngrok...")
        proc.terminate()


if __name__ == "__main__":
    main()
