"""Owner 2026-10-13 item 3: grow the read/change TEST set from the logs with INDEPENDENT truth only (log outcomes and the
owner's own words; never a router or LLM DECISION output). All unique owner messages in the logs were already collected
(176), so growth comes from (a) better log matching for anonymised messages and (b) an EXTENDED rule set made for this
one decision (read vs change), reported SEPARATELY from the strict set:
  undisputed_read   - the logged reply only read/answered (no change made, no approval asked, did not fail) and the
                      owner's next message does NOT dispute the action type ("why didn't you apply/update ...")
  undisputed_change - the logged reply shows a change was made and the owner did NOT say he only wanted a read
  approved_change   - the reply asked for approval of a change and the owner's next message approved it
Complaints about answer CONTENT (wrong number, wrong folder) do not change whether the request was a read or a change.
Output: data/gt_outcome_ext.jsonl (strict rows copied + extended rows; field 'tier': strict|extended). usage: grow_d2.py"""
import json, glob, re, pathlib, difflib, collections
src = (pathlib.Path(__file__).parent / "outcome_labels.py").read_text()
exec(src[:src.index("out, unres = [], []")])
APPROVAL_STRICT = re.compile(r"(\bapprove\b|\bapproval\b|confirm (to|before|and i)|reply (yes|go)|waiting for your)", re.I)   # a CHANGE awaiting approval
APPROVE = re.compile(r"^\W*(yes|approve[d]?|i approve|go ahead|ok(ay)?[, ]+(do it|go|proceed)|do it|proceed|confirmed?)\b", re.I)
# windows that skip system relay lines ("[Member -> Project CTO] ...", logged with role user) and keep them as part of
# the OUTCOME, so a team run's real result (e.g. "zero writes", "deployed") is visible; the owner's next REAL message follows
W2T, W2S = {}, []
for base in (WSP / "Odin-Orchestrator", ROOT):
    for f in glob.glob(str(base / "workspace/chats/scopes/*/chats/*.json")):
        if "/member__" in f: continue
        try: d = json.load(open(f))
        except Exception: continue
        ms = [m for m in ((d.get("messages") if isinstance(d, dict) else d) or []) if isinstance(m, dict)]
        for i, m in enumerate(ms):
            if m.get("role") != "user" or (m.get("content") or "").startswith("["): continue
            j = i + 1; rep = []; relays = []
            while j < len(ms) and (ms[j].get("role") != "user" or (ms[j].get("content") or "").startswith("[")):
                (relays if ms[j].get("role") == "user" else rep).append(ms[j].get("content") or ""); j += 1
            w = {"reply": rep, "relays": relays, "next": (ms[j].get("content") or "") if j < len(ms) else None, "file": f.split("/workspace/")[1]}
            W2T.setdefault(norm(m.get("content")), w)
            try: W2S.append((float(m.get("ts")), w))
            except Exception: pass
RELAY_READ = re.compile(r"(zero writes|read[- ]only|no (files? )?(were )?(changed|written|modified)|nothing (was )?(written|changed|deployed)|no deploy(ment)? (was )?(needed|made|run))", re.I)
RELAY_CHANGE = re.compile(r"(\bdeployed\b|\bupdated (the )?(list|file|trigger)|\bapplied\b|\bwrote\b|\bcreated\b [`'\"]?[\w./-]+\.\w+|\bdeleted\b|\brestarted\b)", re.I)
def window3(x):
    w = W2T.get(norm(x["text"]))
    if w: return w
    ts = resc.get(norm(x["text"]))
    if ts is None: return None
    c = {w["file"]: w for t, w in W2S if abs(t - ts) < 1.0}
    return next(iter(c.values())) if len(c) == 1 else None
def window2(x):
    w = window(x)
    if w: return w
    ts = resc.get(norm(x["text"]))
    if ts is None: return None
    c = {w["file"]: w for t, w in win_by_ts if abs(t - ts) < 1.0}    # the same chat exists in v1 AND the copy -> same file
    return next(iter(c.values())) if len(c) == 1 else None         # still only an unambiguous match
strict = [json.loads(l) for l in open(D / "gt_outcome.jsonl")]
have = {(g["id"], g["decision"]) for g in strict}
rows = [{**g, "tier": "strict"} for g in strict if g["decision"] == "D2_action"]
why = collections.Counter()
for x in real:
    if x["kind"] != "message" or (x["id"], "D2_action") in have or x["text"].startswith("["): continue
    w = window2(x)
    if not w or not w["reply"]: why["no log window / empty reply"] += 1; continue
    rp = "\n".join(w["reply"]); first = w["reply"][0]; nxt = w["next"] or ""; own = bool(nxt) and not nxt.startswith("[")
    disputes_read = own and CHANGE_CORR.search(nxt[:300]); disputes_change = own and READ_CORR.search(nxt[:300]) and not CHANGE_IN_NEXT.search(nxt[:300])
    lab = rule = None
    if FAILED.search(first[:200]): why["reply failed - action unknown"] += 1; continue
    if first.lstrip().startswith("["): why["reply is a team plan/relay (action not visible)"] += 1; continue
    if APPROVAL_STRICT.search(rp) and not TEAM.search(rp):        # (a closing "want me to ...?" offer is not an approval request)
        if own and APPROVE.search(nxt): lab, rule = "change", "approved_change"
        else: why["approval asked, not approved"] += 1; continue
    elif TEAM.search(rp):
        w3 = window3(x); rl = "\n".join((w3 or {}).get("relays") or []); nx3 = ((w3 or {}).get("next") or ""); own3 = bool(nx3)
        passed = re.search(r"✅\s*passed", rl)
        if not passed: why["team run without a passed result"] += 1; continue
        if RELAY_CHANGE.search(rl) and not RELAY_READ.search(rl):
            if own3 and READ_CORR.search(nx3[:300]) and not CHANGE_IN_NEXT.search(nx3[:300]): why["change disputed"] += 1; continue
            lab, rule, nxt = "change", "team_passed_change", nx3
        elif RELAY_READ.search(rl) and not RELAY_CHANGE.search(rl):
            if own3 and CHANGE_CORR.search(nx3[:300]): why["read disputed"] += 1; continue
            lab, rule, nxt = "read", "team_passed_read", nx3
        else: why["team run, mixed/unclear result"] += 1; continue
        rows.append({"id": x["id"], "decision": "D2_action", "label": lab, "rule": rule, "tier": "extended",
                     "evidence": ("RELAYS: " + rl[:200] + " || NEXT: " + nxt)[:300]}); continue
    elif CHANGE_DONE.search(first) or CHANGE_ANY.search(rp) or CHANGE_EXEC.search(first[:400]):
        if disputes_change: why["change disputed"] += 1; continue
        lab, rule = "change", "undisputed_change"
    else:
        if disputes_read: why["read disputed"] += 1; continue
        lab, rule = "read", "undisputed_read"
    rows.append({"id": x["id"], "decision": "D2_action", "label": lab, "rule": rule, "tier": "extended",
                 "evidence": ("REPLY: " + first + " || NEXT: " + nxt)[:300]})
(D / "gt_outcome_ext.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
c = collections.Counter((r["tier"], r["label"]) for r in rows)
print("read/change independent cases:", len(rows), dict(c), "| not labelled:", dict(why))
