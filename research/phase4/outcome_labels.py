"""P4 ground truth that is INDEPENDENT of the LLM being compared (owner correction 2, 2026-10-12).
A real input gets a TEST label only from evidence in the logs, never from an LLM's judgement:
  owner_corr  - the owner's NEXT message corrects the system and states what he wanted ("I'm not asking about deployment, only ...")
  done_ok     - the logged reply shows what was actually DONE (a change, or only an answer), and the owner's next message
                does not complain or correct it (accepted outcome)
  owner_brief - the owner's own words in the project brief state it ("no QA agent", "read-only")
  work_log    - an agent's own chat shows what it actually did over its life (code edits vs. operating/reporting only)
Everything else is UNRESOLVED -> owner review list (Claude's drafts are only the proposed answer there, never truth).
All rules are regexes over the logs, printed with their evidence. Read-only over v1 and the copy.
usage: outcome_labels.py   -> data/gt_outcome.jsonl, data/gt_unresolved.jsonl"""
import json, glob, re, pathlib, collections
ROOT = pathlib.Path(__file__).resolve().parents[2]; WSP = ROOT.parent; D = ROOT / "research/phase4/data"
def norm(t): return re.sub(r"\s+", " ", (t or "").lower()).strip()
real = [json.loads(l) for l in open(D / "labels_draft.jsonl")]
# ── chat windows: user message -> replies until the next user message, + that next owner message
win_by_text, win_by_ts = {}, []
for base in (WSP / "Odin-Orchestrator", ROOT):
    for f in glob.glob(str(base / "workspace/chats/scopes/*/chats/*.json")):
        if "/member__" in f: continue
        try: d = json.load(open(f))
        except Exception: continue
        ms = [m for m in ((d.get("messages") if isinstance(d, dict) else d) or []) if isinstance(m, dict)]
        for i, m in enumerate(ms):
            if m.get("role") != "user": continue
            j = i + 1; rep = []
            while j < len(ms) and ms[j].get("role") != "user": rep.append(ms[j].get("content") or ""); j += 1
            nxt = (ms[j].get("content") or "") if j < len(ms) else None
            w = {"reply": rep, "next": nxt, "file": f.split("/workspace/")[1]}
            win_by_text.setdefault(norm(m.get("content")), w)
            try: win_by_ts.append((float(m.get("ts")), w))
            except Exception: pass
resc = {norm(json.loads(l)["text"]): json.loads(l)["ts"] for l in open(ROOT / "_research/rescued/testset/raw_requests_anon.jsonl")}
def window(x):
    w = win_by_text.get(norm(x["text"]))
    if w: return w
    ts = resc.get(norm(x["text"]))
    if ts is not None:
        c = [w for t, w in win_by_ts if abs(t - ts) < 1.0]
        if len(c) == 1: return c[0]
    return None
READ_CORR = re.compile(r"(i'?m not ask|i am not ask|not asking (you )?(to|about|for)|i only ask|i just (want|asked|need) (to )?(know|check|see)|"
                       r"\bread[- ]only\b|only (check|diagnos|read|report|ask))", re.I)
CHANGE_IN_NEXT = re.compile(r"\b(modify|update|edit|change|fix|deploy it|apply|delete|write)\b", re.I)
CHANGE_CORR = re.compile(r"(why (didn'?t|did not) you (do|apply|update|deploy|fix|change)|i asked you to (update|apply|deploy|fix|change|do|delete)|"
                         r"you (didn'?t|did not) (do|apply|update|deploy|fix|change))", re.I)
COMPLAINT = re.compile(r"\b(no|not|wrong|didn'?t|did not|why|again|redo|retry|stop|violat|drift|mistake|instead|where is|expected)\b", re.I)
CHANGE_DONE = re.compile(r"^\W*(done|redone|deployed|updated|fixed|applied|created|deleted|removed|restarted|rotated|installed|committed|wrote|saved|migrated)\b", re.I)
CHANGE_EXEC = re.compile(r"(approved\W+running \d+ change|running \d+ change\(s\) now|protocol applied|rotat(ed|ing) the firewall|(nsg|ufw)[^\n]{0,40}(rotated|applied|replaced))", re.I)   # 2026-10-13: executed changes the first rules missed
CHANGE_ANY = re.compile(r"(saved to memory|i\'ll remember)|\b(i (updated|deployed|deleted|changed|edited|wrote|restarted|created|removed|rotated|installed|migrated)|re-?rotated|"
                        r"(nsg|ufw)[^.\n]{0,40}(rotated|replaced|updated))", re.I)
ASKS_APPROVAL = re.compile(r"(approve|approval|shall i|should i (go|proceed)|want me to|confirm (to|before|and i)|reply (yes|go)|step 1|do you want|\?\s*$)", re.I)
FAILED = re.compile(r"(not done|never actually happened|was blocked|failed|could ?n[o']t|can'?t|cannot|unable to|error|hit your .{0,10}limit|resets \d)", re.I)
TEAM = re.compile(r"(the team is now running|assigned to (the )?(team|members))", re.I)
ORCH_BUILD = re.compile(r"\b(build|develop|deliver|create)\b[^.\n]{0,80}\b(app|application|platform|dashboard|portal|landing page|product|website|web app|backend|frontend)\b", re.I)
ORCH_SECOND = re.compile(r"(\b(?<!not )(?<!don't )(?<!do not )deploy(?! it yet)\b|\bqa\b|\bassign (the|each)\b|\bdecide the team\b|frontend[^.\n]{0,60}backend|backend[^.\n]{0,60}frontend)", re.I)
out, unres = [], []
def put(x, dec, lab, rule, ev): out.append({"id": x["id"], "decision": dec, "label": lab, "rule": rule, "evidence": ev[:300]})
for x in real:
    if x["kind"] != "message": continue
    w = window(x); got = set()
    # owner 2026-10-13: held-out ORCHESTRATE cases. The owner's OWN words order a build of an app/product AND a second
    # specialist phase (deploy / QA / assign the team / frontend+backend) -> orchestrate (like 'owner_brief' for QA).
    # A team run the owner merely did not complain about is still NOT accepted as proof.
    if not x["text"].startswith("[") and ORCH_BUILD.search(x["text"]) and ORCH_SECOND.search(x["text"]):
        put(x, "D1_mode", "orchestrate", "owner_words", x["text"]); got.add("D1_mode")
    if w:
        rep = "\n".join(w["reply"]); first = (w["reply"][0] if w["reply"] else ""); nxt = w["next"] or ""
        accepted = not COMPLAINT.search(nxt[:120]) and not nxt.startswith("[")
        own = bool(nxt) and not nxt.startswith("[")                # "[A -> B] ..." lines are system relays, not the owner
        if own and READ_CORR.search(nxt[:300]) and not CHANGE_IN_NEXT.search(nxt[:300]):
            put(x, "D2_action", "read", "owner_corr", "NEXT: " + nxt); got.add("D2_action")
        elif own and CHANGE_CORR.search(nxt[:300]):
            put(x, "D2_action", "change", "owner_corr", "NEXT: " + nxt); got.add("D2_action")
        elif rep and accepted and not FAILED.search(first[:200]):
            if CHANGE_DONE.search(first) or CHANGE_ANY.search(rep) or CHANGE_EXEC.search(first[:400]):
                put(x, "D2_action", "change", "done_ok", "REPLY: " + first + " || NEXT: " + nxt); got.add("D2_action")
            elif not ASKS_APPROVAL.search(rep) and not TEAM.search(rep):
                put(x, "D2_action", "read", "done_ok", "REPLY: " + first + " || NEXT: " + nxt); got.add("D2_action")
        if rep and accepted and not FAILED.search(first[:200]):
            # an accepted single direct reply PROVES direct was enough (D1 = minimal handling); an accepted team run does
            # not prove the team was needed, so 'orchestrate' is never taken from acceptance -> owner review
            if "D1_mode" not in got and len(w["reply"]) == 1 and not TEAM.search(rep) and not first.startswith("[") and not ASKS_APPROVAL.search(rep):
                put(x, "D1_mode", "direct", "done_ok", "single reply answered it, accepted. REPLY: " + first + " || NEXT: " + nxt); got.add("D1_mode")
    for dec in ("D1_mode", "D2_agent", "D2_action"):
        if dec not in got: unres.append({"id": x["id"], "decision": dec, "text": x["text"], "proposed": x["labels"][dec], "draft_uncertain": x["uncertain"],
                                        "why": "no log window" if not w else "logs do not show it unambiguously" if dec != "D2_agent" else
                                        "logs record who EXECUTED (mostly the CTO), not which specialist OWNS it"})
# ── D4 goals: owner's own words in the brief; QA findings that led to fixes
NOQA = re.compile(r"(no qa|without (a )?qa|qa (is )?not (needed|required)|skip qa|do not add qa|no (code )?review)", re.I)
for x in real:
    if x["kind"] != "goal": continue
    pid = x["source"].split(":", 1)[1]
    if NOQA.search(x["text"]):
        put(x, "D4_qa", "no", "owner_brief", x["text"])
        continue
    qa = [f for f in glob.glob(str(WSP / "Odin-Orchestrator/workspace/chats/scopes") + "/member__" + pid + "__QA*/chats/*.json") +
          glob.glob(str(ROOT / "workspace/chats/scopes") + "/member__" + pid + "__QA*/chats/*.json")]
    caught = []
    for f in qa:
        try: d = json.load(open(f))
        except Exception: continue
        for m in (d.get("messages") if isinstance(d, dict) else d) or []:
            c = (m.get("content") or "") if isinstance(m, dict) else ""
            if m.get("role") == "assistant" and re.search(r"(\bFAIL\b|verdict: ?fail|found (a |\d+ )?(bug|defect|regression|issue)s?)", c, re.I): caught.append(c[:160])
    if caught:
        put(x, "D4_qa", "yes", "work_log", f"QA caught {len(caught)} real problem(s), e.g.: " + caught[0])
    else:
        unres.append({"id": x["id"], "decision": "D4_qa", "text": x["text"][:300], "proposed": x["labels"]["D4_qa"], "draft_uncertain": x["uncertain"],
                      "why": "brief does not state it and no QA run caught a real problem"})
# ── D9 agents: what the agent actually did in its own chats
CODE_EDIT = re.compile(r"((created|edited|modified|wrote|updated|patched|added) [`'\"]?[\w./-]+\.(py|ts|tsx|js|jsx|dart|sh|go|java|css|html|sql|kt|swift)\b|```diff)", re.I)
for x in real:
    if x["kind"] != "agent": continue
    title = x["text"].split(":")[0].split(" — ")[0].strip().lower()
    files = [f for base in (WSP / "Odin-Orchestrator", ROOT) for f in glob.glob(str(base / "workspace/chats/scopes/member__*/chats/*.json"))
             if f.split("/scopes/member__")[1].split("/")[0].split("__")[-1].strip().lower() == title]
    nrep = edits = 0; ex = ""
    for f in files:
        try: d = json.load(open(f))
        except Exception: continue
        for m in (d.get("messages") if isinstance(d, dict) else d) or []:
            if isinstance(m, dict) and m.get("role") == "assistant":
                nrep += 1; mm = CODE_EDIT.search(m.get("content") or "")
                if mm: edits += 1; ex = ex or mm.group(0)
    unres.append({"id": x["id"], "decision": "D9_nature", "text": x["text"][:300], "proposed": x["labels"]["D9_nature"], "draft_uncertain": x["uncertain"],
                  "why": f"chat text is not reliable proof of code work ({nrep} replies, {edits} mention a code edit) -> owner"})
(D / "gt_outcome.jsonl").write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in out))
(D / "gt_unresolved.jsonl").write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in unres))
c = collections.Counter((o["decision"], o["label"], o["rule"]) for o in out)
for k in sorted(c): print(k, c[k])
print("UNRESOLVED", collections.Counter(o["decision"] for o in unres))
agree = collections.Counter((o["decision"], o["label"] == next(r["labels"][o["decision"]] for r in real if r["id"] == o["id"])) for o in out)
print("draft vs outcome agreement:", dict(agree))
