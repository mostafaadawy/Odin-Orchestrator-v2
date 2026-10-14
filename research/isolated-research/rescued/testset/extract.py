#!/usr/bin/env python3
"""Stage 1-3 of the Keel test-set build: extract owner request texts, dedupe, report counts.
Read-only over workspace/; writes only keel/testset/_work/candidates.jsonl. No network, no LLM."""
import json, glob, re, os, difflib, hashlib, datetime, bisect, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
WS = ROOT / "workspace"
OUT = pathlib.Path(__file__).resolve().parent / "_work"; OUT.mkdir(exist_ok=True)
stats = {}

# Stage 0: routing log (no request text; used only as a join for lead agent / approval)
routes = []
for l in open(WS / "history/routing.jsonl"):
    if not l.strip(): continue
    r = json.loads(l)
    if r.get("ref") == "init": continue
    t = datetime.datetime.strptime(r["ts"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=datetime.timezone.utc).timestamp()
    m = re.match(r"Routed to (.*?); approval=(.*)\.$", r["summary"])
    routes.append((t, m.group(1) if m else "", m.group(2) if m else ""))
routes.sort()
stats["s0_routing_lines"] = sum(1 for l in open(WS / "history/routing.jsonl") if l.strip())
stats["s0_routing_route_events"] = len(routes)
stats["s0_routing_events_with_text_field"] = 0

# Stage 1: all user-role messages in the chat archive
msgs = []
for f in sorted(glob.glob(str(WS / "chats/**/*.json"), recursive=True)):
    try: d = json.load(open(f))
    except Exception: continue
    if not isinstance(d, dict) or "messages" not in d: continue
    for m in d["messages"]:
        if m.get("role") == "user":
            msgs.append(dict(scope=d.get("scope") or "", ts=float(m.get("ts") or 0), raw=str(m.get("content", ""))))
stats["s1_chat_user_messages"] = len(msgs)

harness_txt = "\n".join(open(p, errors="ignore").read() for p in glob.glob(str(WS / "shared/testing/*.py")))
harness_norm = re.sub(r"\s+", " ", harness_txt)
WRAP = re.compile(r"^\[Chief Engineer → Project CTO\]\s*(?:For '[^']*':\s*)?", re.S)
SUFFIX = re.compile(r"\.?\s*Plan it, assign the team, and report back\.?\s*$", re.S)
DRILL = re.compile(r"^(DRILL|COMPLETE THE|SOLVE THE|Final tight pass|MAIN DIAGNOSIS)")

def classify(m):
    c = m["raw"].strip()
    if c.startswith("[Chief Engineer → Project CTO]"):
        c = SUFFIX.sub("", WRAP.sub("", c)).strip()
        if c.startswith("[Chief Engineer → Project CTO]"):  # double-wrapped
            c = SUFFIX.sub("", WRAP.sub("", c)).strip()
        q = re.search(r"QUESTION:\s*(.*?)\s*LIVE READ-ONLY DATA", c, re.S)
        if q: return "owner_via_anchor", q.group(1)
        if c.startswith("OWNER'S INSTRUCTIONS"): return "owner_scheduled_instruction", c
        if DRILL.match(c): return "operator_drill", c
        if re.sub(r"\s+", " ", c)[:70] in harness_norm: return "harness_prompt", c
        if c.startswith("Run this project's recurring"): return "ui_template", c
        return "owner_relayed", c
    if re.match(r"^\[(Scheduled task|Manual run)\]", c) or c.startswith("Run this project's recurring") or c.startswith("▶ Run the recurring"):
        return "ui_template", c
    if re.match(r"^\s*\[[^\]]{0,60}\]", c): return "agent_or_system", c
    return "owner_direct", c

for m in msgs: m["source"], m["text"] = classify(m)
from collections import Counter
stats["s1_by_source"] = dict(Counter(m["source"] for m in msgs))
owner = [m for m in msgs if m["source"].startswith("owner")]
stats["s2_owner_authored"] = len(owner)

def norm(s):
    s = s.lower(); s = re.sub(r"[^\w\s]", " ", s); return re.sub(r"\s+", " ", s).strip()
owner.sort(key=lambda m: m["ts"])
exact, seen = [], {}
for m in owner:
    k = norm(m["text"])
    if k in seen: seen[k]["dups"] += 1; seen[k]["dup_ts"].append(m["ts"]); continue
    m["dups"] = 0; m["dup_ts"] = []; seen[k] = m; exact.append(m)
stats["s3_after_exact_dedupe"] = len(exact)
near = []
for m in exact:
    k = norm(m["text"])
    hit = next((n for n in near if difflib.SequenceMatcher(None, k, norm(n["text"])).ratio() >= 0.90), None)
    if hit: hit["dups"] += 1 + m["dups"]; hit["dup_ts"] += [m["ts"]] + m["dup_ts"]; continue
    near.append(m)
stats["s4_after_near_dedupe_0.90"] = len(near)

rts = [r[0] for r in routes]
def route_for(ts, w=180):
    i = bisect.bisect_left(rts, ts - w)
    return routes[i] if i < len(routes) and routes[i][0] <= ts + w else None
joined = 0
with open(OUT / "candidates.jsonl", "w") as fo:
    for m in near:
        r = route_for(m["ts"]); joined += bool(r)
        cid = hashlib.sha1(norm(m["text"]).encode()).hexdigest()[:8]
        fo.write(json.dumps(dict(cid=cid, ts=m["ts"], scope=m["scope"], source=m["source"], dups=m["dups"],
                                 route_lead=(r[1] if r else None), route_approval=(r[2] if r else None),
                                 text=m["text"]), ensure_ascii=False) + "\n")
stats["s4_candidates_joined_to_routing"] = joined
json.dump(stats, open(OUT / "extract_stats.json", "w"), indent=1)
print(json.dumps(stats, indent=1))
