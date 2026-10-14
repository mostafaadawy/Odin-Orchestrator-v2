"""P4d-1 (owner correction 1, 2026-10-12): more examples where classes were thin.
 - D9 agent nature: 20 descriptions for EACH agent family seen in Odin's real roster (generic families, never the
   real descriptions themselves, so the test set does not leak into training);
 - D1 orchestrate: extra messages that genuinely need several specialists, plus look-alike direct ones.
Same generator, same definitions and same leakage filter as gen_train.py. Saves every batch (resumable).
Output: data/train_gen_extra.jsonl. usage: gen_extra.py"""
import pathlib, json, os, concurrent.futures as cf
_src = (pathlib.Path(__file__).parent / "gen_train.py").read_text()
exec(_src[:_src.index("jobs = [")])          # shared header: R-ZC check, SPEC, ask(), gen_messages(), filters
FAMILIES = ["CRM platform operator (contacts, companies, deals via API)", "email-marketing platform operator (lists, flows, profiles)",
 "shipping / fulfillment status operator", "e-commerce order and product data operator", "social-media content creator / poster",
 "content writer and campaign copy agent", "sales pipeline assistant", "business analytics / KPI reporter", "reporting and documentation agent",
 "SOC investigator (alerts, incidents, triage)", "threat-hunting / security intelligence architect", "intrusion detection and behavioural analytics agent",
 "threat prediction and prevention agent", "asset, exposure and attack-surface agent", "identity and access governance agent",
 "vulnerability and patch management agent", "compliance / configuration-baseline agent", "detection engineering and purple-team validation agent",
 "recovery and resilience (backup/restore) agent", "audio capture agent for meetings", "speech transcription agent", "text chunking agent",
 "chunk analysis agent", "final summary agent", "notification agent", "memory and storage agent", "CTO / orchestrator agent that plans and delegates",
 "operational QA reviewer that checks reports and runs", "code QA / test engineer that writes and runs tests", "DevOps engineer (deploys, CI/CD, servers)",
 "cloud debugging / incident engineer", "full-stack developer", "frontend developer", "backend / API developer", "mobile app developer",
 "database engineer (schema, migrations)", "data engineer (pipelines, ETL code)", "ML engineer (training and serving models)", "security engineer who writes fixes in code"]
def gen_family(fam, seed):
    p = (f"You generate TRAINING DATA for Odin, an AI software-company orchestrator. Write 20 DIFFERENT one-line AI team-member descriptions "
         f"in the form '<Name> — <Role>: <what it does>' for this family of agent: {fam}. Vary names, tools, platforms and wording widely "
         f"(seed {seed}); some members of a family may write code and some only operate tools — label each by what IT does.\n"
         "Label each nature: 'technical' if it writes/edits code or builds software components, else 'operational' (operates platforms via API, "
         "reports, analyses, monitors, coordinates — no code). "
         'Reply with ONLY a JSON array: [{"text": "...", "nature": "technical|operational"}]')
    return [{"kind": "agent", "text": a["text"], "labels": {"D9_nature": a["nature"]}, "family": fam} for a in ask(p)
            if isinstance(a, dict) and a.get("text") and a.get("nature") in ("technical", "operational")]
ORCH = ["requests that genuinely need SEVERAL specialists to build or ship something (apps, portals, dashboards, integrations end-to-end, build+test+deploy) — mode orchestrate",
        "requests that LOOK big but are a single scoped task, a question, an approval or a read-only diagnosis — mode direct (hard negatives for orchestrate)"]
jobs = [("f", fam, 0) for fam in FAMILIES] + [("o", f, s) for s in range(4) for f in ORCH]
PARTS = ROOT / "research/phase4/data/gen_parts_extra"; PARTS.mkdir(parents=True, exist_ok=True)
def run(ij):
    i, (k, f, s) = ij; part = PARTS / f"{i:03d}.json"
    if part.exists(): return i, json.loads(part.read_text()), True
    r = gen_family(f, s) if k == "f" else gen_messages(f, 100 + s)
    if r: part.write_text(json.dumps(r, ensure_ascii=False))
    return i, r, False
res, zero = [], 0
with cf.ThreadPoolExecutor(int(os.environ.get("P4_PAR", "3"))) as ex:
    for i, r, c in ex.map(run, list(enumerate(jobs))):
        res += r; zero = 0 if r else zero + 1
        print(f"extra {i+1}/{len(jobs)}: +{len(r)}{' (saved earlier)' if c else ''} (total {len(res)})", flush=True)
        if zero >= 4: print("STOP: 4 empty batches in a row - rerun later", flush=True); ex.shutdown(wait=False, cancel_futures=True); raise SystemExit(3)
missing = [i for i in range(len(jobs)) if not (PARTS / f"{i:03d}.json").exists()]
if missing: print("INCOMPLETE:", missing, flush=True)
(ROOT / "research/phase4/data/train_gen_extra.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in res))
print("DONE", len(res))
