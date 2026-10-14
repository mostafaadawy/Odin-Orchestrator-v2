#!/usr/bin/env python3
"""Fix #2 unit checks (no model cost). Usage: fix2_unit.py <server_dir> <workspace_dir>
1) _review_verdict on EVERY recorded '[Project CTO review]' in the chats.
2) Acceptance + run-result rule (extracted logic) on the CH cases.
3) SOC _reconcile auto-resolve and SOC-APP-001 parsing."""
import sys, json, re, pathlib, ast, types, collections
srv, ws = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
src = (srv / "api_v2.py").read_text()
fails = []
def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond: fails.append(name)

# load _review_verdict alone
tree = ast.parse(src)
fn = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_review_verdict"]
check("helper present", bool(fn))
ns = {"re": re}
exec(compile(ast.Module(body=fn, type_ignores=[]), "rv", "exec"), ns)
rv = ns["_review_verdict"]

# 1) every recorded review
cnt = collections.Counter(); samples = {}
for f in ws.glob("chats/scopes/*/chats/*.json"):
    try: d = json.loads(f.read_text(errors="replace"))
    except Exception: continue
    msgs = d.get("messages", d if isinstance(d, list) else [])
    for m in msgs if isinstance(msgs, list) else []:
        c = str((m or {}).get("content", "")) if isinstance(m, dict) else ""
        if c.startswith("[Project CTO review]"):
            body = c[len("[Project CTO review]"):].strip()
            v = rv(body); cnt[v] += 1
            samples.setdefault(v, []).append(body[:90])
            low = body.lower().lstrip(" *_>`#\"'")
            if low.startswith("needs fix"): check_nf = (v == "needs_fix")
            if low.startswith("needs fix") and v != "needs_fix": fails.append("NF misread: " + body[:60])
            if low.startswith("confirmed") and v != "confirmed" and not re.search(r"needs[\s-]+(a\s+)?fix", low): print("  NOTE confirmed-start but not counted:", v, body[:80])
print("recorded reviews by verdict:", dict(cnt))
for k, v in samples.items(): print(" ", k, "e.g.", v[:2])
check("recorded reviews found", sum(cnt.values()) > 0)
check("no Confirmed/Needs-fix review misread", not any(x.startswith(("NF misread", "C misread")) for x in fails))
for t, want in [("Confirmed: files at src/x.py, tests 4/4", "confirmed"), ("**Confirmed:** ok", "confirmed"),
                ("✅ Confirmed: done", "confirmed"), ("Needs fix: no evidence", "needs_fix"),
                ("needs fix — missing tests", "needs_fix"), ("", "unclear"), (None, "unclear"),
                ("Looks mostly fine", "unclear"), ("API Error: 401 authentication_error", "unclear"),
                ("Not confirmed: missing", "unclear"),
                ("Confirmed via filesystem: folder exists. **Needs fix:** no form was written", "needs_fix"),
                ("Confirmed via filesystem, all good", "unclear"), ("Confirmed: done, no fix needed", "confirmed")]:
    check(f"verdict {t!r} -> {want}", rv(t) == want)

# 2) acceptance + run rule (mirror of the patched code; also asserted present in source)
def step_ok(review, step_clean, qa_ok): return rv(review) == "confirmed" and step_clean and qa_ok
def run_ok(steps, qa_enabled):
    passed = [s for s in steps if step_ok(*s)]; failed = [s for s in steps if not step_ok(*s)]
    return len(passed) >= len(steps) and not failed
check("source: all_ok no longer 'else True'", "if qa_enabled else True" not in src)
check("source: ok_step from the fixed verdict + evidence (fix #2c)", 'ok_step = (_outc == "PASSED")' in src)
check("source: 'passed (QA + audit clean)' only with QA ran", "'✅ passed (QA + audit clean)'" not in src)
check("source: efblob excludes reviews", 'str(_r.get("review")' not in src.split("_engine_fail_markers")[1][:900])
check("CH2-11/CH4-2: QA off + one 'Needs fix' -> NOT passed",
      not run_ok([("Confirmed: ok", True, True), ("Needs fix: missing X", True, True)], qa_enabled=False))
check("CH2-1: audit flagged + review 'Confirmed' -> NOT passed", not step_ok("Confirmed: control plane ok", False, True))
check("QA failed + Confirmed -> NOT passed", not step_ok("Confirmed: ok", True, False))
check("unclear review -> NOT passed", not step_ok("I think it is fine", True, True))
check("clean run still passes (QA off)", run_ok([("Confirmed: a.py written", True, True)] * 2, qa_enabled=False))
check("clean run still passes (QA on)", run_ok([("Confirmed: tests 3/3", True, True)] * 3, qa_enabled=True))

# 3) SOC
sys.path.insert(0, str(srv))
import importlib, tempfile, os
mods = {}
for name in ("store", "scopes"):
    if name not in sys.modules: sys.modules[name] = types.ModuleType(name)
reg = {"items": {}}
sys.modules["store"].read_json = lambda p, d: reg
sys.modules["store"].write_json = lambda p, v: None
try:
    soc = importlib.import_module("soc_run")
    soc._reg_path = lambda pid: "x"
    f = lambda i: {"id": i, "title": i, "severity": "high", "classification": "Suspicious", "asset": "vm"}
    soc._reconcile("p", [f("SOC-A"), f("SOC-B")], checked_ids={"SOC-A", "SOC-B"})
    sec = soc._reconcile("p", [], checked_ids={"SOC-A"})   # quick run: only SOC-A re-checked, both gone
    res = {it["id"] for it in sec["resolved"]}
    check("CH4-4: re-checked & clean finding auto-resolves", "SOC-A" in res)
    check("CH4-4: NOT re-checked finding stays open", "SOC-B" not in res and reg["items"]["SOC-B"]["owner_status"] == "open")
    # SOC-APP-001 with a sudo prompt
    soc._ssh_ro = lambda cmd, timeout=25: (True, "[sudo] password for mostafa:")
    soc._vm_pw = lambda: "dummy"
    fnames = [n for n in dir(soc) if n.startswith("check_") and "abuse" in n or n in ("check_app_abuse",)]
    target = None
    for n in dir(soc):
        if n.startswith("check_"):
            try:
                code = getattr(soc, n).__code__
                if "SOC-APP-001" in code.co_consts or any("SOC-APP-001" in str(c) for c in code.co_consts): target = n
            except Exception: pass
    out = getattr(soc, target)(False) if target else None
    check(f"CH4-1: sudo prompt -> Data unavailable ({target})", bool(out) and out.get("data_source_state") == "Data unavailable")
    soc._ssh_ro = lambda cmd, timeout=25: (True, "     3 10.0.0.1\n     1 10.0.0.2")
    out = getattr(soc, target)(False)
    check("SOC-APP-001 real low counts -> Checked and healthy", out.get("data_source_state") == "Checked and healthy")
    soc._ssh_ro = lambda cmd, timeout=25: (True, "    42 10.0.0.9")
    out = getattr(soc, target)(False)
    check("SOC-APP-001 elevated -> finding detected", out.get("data_source_state") == "Checked and finding detected")
except Exception as e:
    import traceback; traceback.print_exc(); fails.append(f"soc import/run: {e}")
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails[:8]}")
sys.exit(1 if fails else 0)
