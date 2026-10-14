"""Phase 4a-2 / 4d: collect REAL inputs (read-only) for the decision points.
  messages : owner messages -> D1 (direct/orchestrate), D2 (specialist + read/change)
  agents   : agent descriptions -> D9 (technical/operational)
  goals    : project goals/briefs -> D4 (recommend QA yes/no)
Sources: the rescued anonymised request set, owner messages in copy + v1 chat scopes (read-only), scenario
prompts, project briefs. Output: research/phase4/data/real_inputs.jsonl (dedup by normalised text)."""
import json, glob, re, pathlib, hashlib, sys, os
ROOT = pathlib.Path(__file__).resolve().parents[2]; WSP = ROOT.parent
out, seen = [], set()
def norm(t): return re.sub(r"\s+", " ", t.lower()).strip()
def add(kind, text, source, **meta):
    t = (text or "").strip()
    if len(t) < 8 or len(t) > 3500: return
    k = (kind, norm(t))
    if k in seen: return
    seen.add(k); out.append({"id": hashlib.sha1(f"{kind}|{norm(t)}".encode()).hexdigest()[:12], "kind": kind, "text": t, "source": source, **meta})
for l in open(ROOT / "_research/rescued/testset/raw_requests_anon.jsonl"):
    r = json.loads(l); add("message", r["text"], "rescued_testset", logged_lead=r.get("route_lead"), logged_approval=r.get("route_approval"))
for base in (ROOT, WSP / "Odin-Orchestrator"):
    for f in glob.glob(str(base / "workspace/chats/scopes/*/chats/*.json")):
        scope = f.split("/scopes/")[1].split("/")[0]
        if scope.startswith("member__"): continue
        try: d = json.load(open(f))
        except Exception: continue
        for m in (d.get("messages") if isinstance(d, dict) else d) or []:
            if isinstance(m, dict) and m.get("role") == "user":
                c = (m.get("content") or "").strip()
                if not c.startswith(("[", "↳", "▶", "✅")):
                    add("message", c, "chat:" + ("v1" if "Orchestrator" in str(base) else "copy"), scope=scope.split("__")[0])
src = (ROOT / "_consolidation/scenarios.py").read_text()
for m in re.finditer(r'prompt = \(f?"(.+?)"\)', src, re.S):
    add("message", re.sub(r'"\s*f?"', "", m.group(1)).replace("{rep}", "1"), "scenario")
for f in sorted(glob.glob(str(ROOT / "workspace/agents/*/capability.md"))):
    t = pathlib.Path(f).read_text(errors="replace"); lines = [x for x in t.splitlines() if x.strip()]
    title = lines[0].lstrip("# ").strip() if lines else ""; desc = lines[1].strip() if len(lines) > 1 else ""
    add("agent", f"{title}: {desc}", "agents/" + pathlib.Path(f).parent.name)
sys.path.insert(0, str(ROOT / "server"))
try:
    import projects
    for p in projects.list_projects():
        d = (p.get("description") or "").strip()
        if d: add("goal", f"{p.get('name')}: {d[:2500]}", "project:" + str(p.get("id")))
except Exception as e:
    print("projects unavailable:", e)
o = ROOT / "research/phase4/data/real_inputs.jsonl"
o.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out))
from collections import Counter
print(len(out), Counter(x["kind"] for x in out), Counter(x["source"].split(":")[0].split("/")[0] for x in out))
