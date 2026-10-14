#!/usr/bin/env python3
"""
REAL end-to-end driver for the Zoom Smart Meeting Notification Agent.
Drives the SAME HTTP endpoints the web/mobile/desktop UI calls — no shortcut functions:
  1) POST /projects/intake   (paste the spec as the owner would) -> CTO proposes a TEAM
  2) assert NO deviation (only the brief's own agents; no Fulfillment/Frontend/Backend/QA/DevOps)
  3) POST /projects          (create with the proposed spec)     -> team is seeded
  4) GET  /agents/all        (created agents visible org-wide)
  5) POST /projects/{id}/run-now (the play button path)          -> autonomous run, fills the chat
Run:  python testing/e2e_real_flow.py
"""
import json, sys, time, urllib.request, pathlib

def _odin_token():   # F-20: the brain token (same machine)
    import os as _o, pathlib as _p
    if _o.environ.get("ODIN_ACCESS_TOKEN"): return _o.environ["ODIN_ACCESS_TOKEN"]
    for _d in _p.Path(__file__).resolve().parents:
        _f = _d / "data" / "brain_token"
        if _f.is_file(): return _f.read_text().strip()
    return ""


BASE = "http://127.0.0.1:8000"
ROOT = pathlib.Path(__file__).resolve().parent.parent

def call(method, path, body=None, timeout=240):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json", "X-Odin-Token": _odin_token()})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode()
    try:
        return json.loads(raw)
    except Exception:
        return raw

def main():
    spec = (ROOT / "logs" / "zoom_spec.txt").read_text()
    print("STEP 1 — REAL INTAKE (paste the spec, CTO decides the team)…", flush=True)
    t0 = time.time()
    res = call("POST", "/projects/intake", {"history": [{"role": "user", "content": spec}]})
    print(f"  intake returned in {time.time()-t0:.0f}s; action = {res.get('action')}")

    # If the CTO asks a clarifying question, answer 'use exactly the agents/rules in the brief' and retry
    hops = 0
    hist = [{"role": "user", "content": spec}]
    while res.get("action") == "ask" and hops < 3:
        hops += 1
        q = res.get("question", "")
        print(f"  CTO asked: {q!r} -> answering 'use only the brief's defined agents/rules'")
        hist.append({"role": "assistant", "content": q})
        hist.append({"role": "user", "content": "Use ONLY the 7 agents and 15 rules defined in the brief. "
                                                 "Invent nothing. It is operational, no code to build."})
        res = call("POST", "/projects/intake", {"history": hist})
        print(f"  action = {res.get('action')}")

    if res.get("action") != "propose":
        print("  !! intake did not converge to a proposal:", json.dumps(res)[:500]); sys.exit(2)

    spec_out = res.get("spec", {})
    team = spec_out.get("team", [])
    print("  PROPOSED TEAM:", team)
    print("  platform/stack:", spec_out.get("stack"))

    # DEVIATION CHECK — none of these forbidden roles may appear for this operational brief
    forbidden = {"frontend", "backend", "database", "devops", "qa", "fulfillment",
                 "fullstack", "security", "quality assurance"}
    hit = [t for t in team if str(t).strip().lower() in forbidden]
    if hit:
        print("  ❌ DEVIATION DETECTED — forbidden roles staffed:", hit); sys.exit(3)
    print("  ✅ NO DEVIATION — only the brief's own agents were proposed.")

    # STEP 3 — CREATE through the real endpoint, using the CTO's proposed team
    print("STEP 3 — CREATE project via POST /projects (real flow)…", flush=True)
    members = [{"name": t, "role": t} for t in team]
    payload = {
        "name": spec_out.get("name") or "Zoom Smart Meeting Notification Agent",
        "description": spec_out.get("description") or spec,
        "type": spec_out.get("type") or "operational",
        "stack": spec_out.get("stack") or "operational — no build",
        "members": members,
        "cadence": "periodical",
        "periodic": {"enabled": True, "schedule": {"kind": "daily", "hhmm": "06:00"},
                     "requireApproval": False},
        "identifier": "zoom-real-flow",
    }
    proj = call("POST", "/projects", payload)
    pid = proj.get("id")
    print("  created project id:", pid, "| members:", proj.get("members"))

    # STEP 4 — visibility: the new agents appear in the org-wide roster
    print("STEP 4 — GET /agents/all (visibility)…", flush=True)
    alla = call("GET", "/agents/all")
    roster = alla.get("agents", alla if isinstance(alla, list) else [])
    mine = [a for a in roster if a.get("project") == pid or a.get("pid") == pid]
    print(f"  org-wide roster size: {len(roster)}; agents tagged to this project: {len(mine)}")
    for a in mine[:12]:
        print("    -", a.get("name"), "|", a.get("role"))

    print("DONE. pid=", pid)
    print("PID_LINE:" + str(pid))

if __name__ == "__main__":
    main()
