"""P4d-1: training data generated with Claude Code (plan login, R-ZC) from Odin's REAL context — the real project
names, real agent roster, and the exact decision definitions Odin's own prompts use. Real test inputs are NEVER
shown to the generator; a leakage check later drops any example too close to a real input.
Output: research/phase4/data/train_gen.jsonl  ({kind, text, labels}). usage: gen_train.py"""
import sys, os, json, re, pathlib, random, concurrent.futures as cf
ROOT = pathlib.Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "server"))
os.environ["ODIN_CLAUDE_TOOLS"] = "Read"          # generation needs no tools
import claude_cli, projects
prob = claude_cli.paid_auth_problem()
if prob: print("R-ZC STOP:", prob); sys.exit(3)
real = [json.loads(l) for l in open(ROOT / "research/phase4/data/real_inputs.jsonl")]
PROJ = sorted({x["text"].split(":")[0] for x in real if x["kind"] == "goal"})
AGENTS = sorted({x["text"].split(" — ")[0] for x in real if x["kind"] == "agent"})
SPEC = ("Specialists (route by the ACTION, not by names inside file/folder names):\n"
        "- Frontend: UI/UX, components, styling, client screens, web pages.\n- Backend: APIs, services, business logic, integrations (orders, CRM contacts, email platform data), jobs, billing logic.\n"
        "- DevOps & Cloud: anything on a server or VM (Azure), deploys, deploy lists, infra, files/folders ON a remote machine, SSH, firewall/dynamic-IP protocol, nginx, systemd, networking.\n"
        "- Security & Compliance: secrets, keys, auth, encryption, PII, audits, exposure, fake users/abuse.\n- QA & Testing: tests, regressions, verification.\n"
        "- Database: schema, tables, migrations, queries, backups.\n- CTO Brain: strategy, planning, greetings, questions about the assistant itself, status, or anything that fits none of the above.\n"
        "action: 'read' if it only inspects/answers (compare, list, show, status, check, count, questions); 'change' if it would deploy, restart, write, edit, install, migrate, delete, rotate firewall IPs, approve, redo a change, or modify ANY state; if unsure 'change'.\n"
        "mode: 'direct' if a single scoped task, a question, a confirmation, an approval, or a read-only diagnosis; 'orchestrate' ONLY if it genuinely needs several specialists building/deploying (e.g. build an app, build+QA+deploy).")
FOCUS = ["greetings, pings, test messages and questions about the assistant itself (who are you, capabilities, how many agents)",
         "questions about live business data: orders this week/month, shipping status, CRM contacts and companies, email profiles/lists/workflows",
         "VM / server operations: status, health, list folders over SSH with the dynamic-IP firewall protocol, logs, journalctl, nginx, services",
         "deployments: check whether a deploy is needed, update deploy trigger lists, deploy with/without DB rebase, approvals of deploys",
         "security: secrets, keys, fake sign-ups and app abuse, audits, exposure, login security between apps",
         "building software that needs several specialists: apps, dashboards, landing pages with forms, internal tools, full-stack products",
         "frontend/UI changes: screens, styling, components, web and mobile client issues",
         "database work: schema, migrations, queries, backups, data integrity checks",
         "testing and verification requests: run tests, regressions, verify a fix",
         "follow-ups in an ongoing chat: redo, retry, confirm, approve, complaints that the assistant drifted or violated rules"]
def _objs(raw):
    """Robust: the whole array if it parses, else every {...} object that parses on its own."""
    raw = raw or ""
    try:
        a = json.loads(raw[raw.index("["): raw.rindex("]") + 1])
        if isinstance(a, list): return a
    except Exception:
        pass
    out, dec, i = [], json.JSONDecoder(), 0
    while True:
        i = raw.find("{", i)
        if i < 0: break
        try:
            o, j = dec.raw_decode(raw, i); out.append(o); i = j
        except Exception:
            i += 1
    return out
_ALIAS = {"devops": "DevOps & Cloud", "devops & cloud": "DevOps & Cloud", "cloud": "DevOps & Cloud", "security": "Security & Compliance",
          "security & compliance": "Security & Compliance", "qa": "QA & Testing", "qa & testing": "QA & Testing", "testing": "QA & Testing",
          "cto": "CTO Brain", "cto brain": "CTO Brain", "frontend": "Frontend", "backend": "Backend", "database": "Database", "db": "Database"}
def ask(prompt):
    best = []
    for _ in range(2):
        raw = claude_cli.ClaudeCLIBrain().respond(prompt, lang="en")
        a = [x for x in _objs(raw) if isinstance(x, dict)]
        for x in a:
            if "agent" in x: x["agent"] = _ALIAS.get(str(x["agent"]).strip().lower(), x["agent"])
            for k in ("mode", "action", "nature", "qa"):
                if k in x: x[k] = str(x[k]).strip().lower()
        if len(a) > len(best): best = a
        if len(best) >= 15: break
    return best
def gen_messages(focus, seed):
    p = (f"You generate TRAINING DATA for Odin, an AI software-company orchestrator. Write 30 DIFFERENT realistic messages the "
         f"owner might type in chat, focused on: {focus}. Style: short, informal, sometimes typos, sometimes Arabic, sometimes long "
         f"instructions; mention real names where natural — projects: {', '.join(PROJ[:30])}; agents: {', '.join(AGENTS[:25])}. "
         f"Vary wording widely (seed {seed}); never copy each other.\n\nLabel EACH message using exactly these definitions:\n{SPEC}\n\n"
         'Reply with ONLY a JSON array: [{"text": "...", "mode": "direct|orchestrate", "agent": "<one specialist name exactly>", "action": "read|change"}]')
    out = []
    for a in ask(p):
        if isinstance(a, dict) and a.get("text") and a.get("mode") in ("direct", "orchestrate") and a.get("action") in ("read", "change") \
                and a.get("agent") in ("Frontend", "Backend", "DevOps & Cloud", "Security & Compliance", "QA & Testing", "Database", "CTO Brain"):
            out.append({"kind": "message", "text": a["text"], "labels": {"D1_mode": a["mode"], "D2_agent": a["agent"], "D2_action": a["action"]}})
    return out
def gen_agents(seed):
    p = (f"You generate TRAINING DATA for Odin. Write 25 DIFFERENT one-line AI team-member descriptions in the form '<Name> — <Role>: <what it does>' "
         f"like a software company would have (engineers, operators of platforms via API, security analysts, reporters, content, SOC agents, meeting/AI pipeline agents). "
         f"Seed {seed}. Label each nature: 'technical' if it writes/edits code or builds software components, else 'operational'. "
         'Reply with ONLY a JSON array: [{"text": "...", "nature": "technical|operational"}]')
    return [{"kind": "agent", "text": a["text"], "labels": {"D9_nature": a["nature"]}} for a in ask(p)
            if isinstance(a, dict) and a.get("text") and a.get("nature") in ("technical", "operational")]
def gen_goals(seed):
    p = (f"You generate TRAINING DATA for Odin. Write 25 DIFFERENT project briefs '<Project name>: <brief>' (1-4 sentences) like: read-only reporting on a platform, "
         f"deploy setup on a sandbox VM, building a web app, SOC monitoring, content automation, tiny utilities, with explicit owner constraints sometimes "
         f"(e.g. 'no QA agent', 'read-only', 'do not deploy'). Seed {seed}. Label qa: 'yes' ONLY if adding a QA gate materially reduces real risk "
         f"(real code changes, production, data integrity) and the owner did not rule QA out; 'no' for pure ops/deploy/sync/read-only/trivial work. "
         'Reply with ONLY a JSON array: [{"text": "...", "qa": "yes|no"}]')
    return [{"kind": "goal", "text": a["text"], "labels": {"D4_qa": a["qa"]}} for a in ask(p)
            if isinstance(a, dict) and a.get("text") and a.get("qa") in ("yes", "no")]
jobs = [("m", f, s) for s in range(3) for f in FOCUS] + [("a", None, s) for s in range(8)] + [("g", None, s) for s in range(8)]
PARTS = ROOT / "research/phase4/data/gen_parts"; PARTS.mkdir(parents=True, exist_ok=True)
_pa = claude_cli.paid_auth_problem()
if _pa: raise SystemExit("R-ZC STOP: " + _pa)
def run(ij):
    i, (k, f, s) = ij
    part = PARTS / f"{i:03d}.json"
    if part.exists(): return i, json.loads(part.read_text()), True
    r = gen_messages(f, s) if k == "m" else gen_agents(s) if k == "a" else gen_goals(s)
    if r: part.write_text(json.dumps(r, ensure_ascii=False))   # empty batches are NOT saved, so a rerun retries them
    return i, r, False
res, zero_run = [], 0
with cf.ThreadPoolExecutor(int(os.environ.get("P4_PAR", "3"))) as ex:
    for i, r, cached in ex.map(run, list(enumerate(jobs))):
        res += r; zero_run = 0 if r else zero_run + 1
        print(f"batch {i+1}/{len(jobs)}: +{len(r)}{' (saved earlier)' if cached else ''} (total {len(res)})", flush=True)
        if zero_run >= 4:
            print("STOP: 4 empty batches in a row (plan limit or sleep?) - rerun later; saved batches are kept", flush=True)
            ex.shutdown(wait=False, cancel_futures=True); raise SystemExit(3)
missing = [i for i in range(len(jobs)) if not (PARTS / f"{i:03d}.json").exists()]
if missing: print("INCOMPLETE, empty batches:", missing, "- rerun to retry them", flush=True)
(ROOT / "research/phase4/data/train_gen.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in res))
from collections import Counter
print("DONE", len(res), Counter(x["kind"] for x in res))
