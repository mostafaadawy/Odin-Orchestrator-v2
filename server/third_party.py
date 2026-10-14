#!/usr/bin/env python3
"""
third_party.py — CLI third-party simulator. Sends ONE prompt to the anchor as an external
app and waits for the result (same contract as the HTML simulator).

Run:
  python3 server/third_party.py --project <pid> --prompt "How many orders this week?"
  python3 server/third_party.py --anchor http://localhost:9100 --project <pid> --prompt "..."
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.request
import urllib.error


def _key() -> str:
    try:
        from integrations import cred
        return cred.get("ANCHOR_API_KEY", "")
    except Exception:
        return ""


def call(base, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(base + path, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    k = _key()
    if k:
        r.add_header("X-API-Key", k)
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read().decode() or "{}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anchor", default="http://localhost:9100")
    ap.add_argument("--project", required=True)
    ap.add_argument("--prompt", required=True)
    args = ap.parse_args()
    base = args.anchor.rstrip("/")

    print(f"[third-party] → POST {base}/anchor/v1/requests  project={args.project}")
    created = call(base, "POST", "/anchor/v1/requests",
                   {"project": args.project, "prompt": args.prompt, "webhook_url": "", "sender": "third-party-cli"})
    rid = created.get("request_id")
    print(f"[third-party] queued: {rid} ({created.get('status')})")
    seen = set()
    for _ in range(200):
        time.sleep(3)
        d = call(base, "GET", f"/anchor/v1/requests/{rid}")
        if d.get("status") not in seen:
            seen.add(d.get("status"))
            print(f"[third-party]   • {d.get('status')}")
        if d.get("status") in ("finished", "failed", "cancelled"):
            print(f"\n[third-party] {d.get('status').upper()}  acked={d.get('acked')}  webhook×{d.get('webhook_attempts', 0)}")
            print("\nRESULT:\n" + (d.get("result") if isinstance(d.get("result"), str) else json.dumps(d.get("result"), indent=2)))
            return
    print("[third-party] timed out")


if __name__ == "__main__":
    main()
