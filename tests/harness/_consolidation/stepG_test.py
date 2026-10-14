#!/usr/bin/env python3
"""Step G / P8-2 + R-DP: deploy.sh obeys the owner's dry-run and deployment rules. Runs deploy.sh against STUB
az/ssh/sshpass/rsync/curl (nothing leaves this Mac; no VM is touched). python stepG_test.py <deploy.sh> <copy-root>"""
import os, sys, subprocess, tempfile, pathlib, shutil, json, re
dsh, iso = pathlib.Path(sys.argv[1]).resolve(), pathlib.Path(sys.argv[2]).resolve()
fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:400]}]" if info and not c else ""))
    if not c: fails.append(n)
W = pathlib.Path(tempfile.mkdtemp(prefix="stepG_")).resolve()
STUB = W / "stub"; STUB.mkdir()
def stub(name, body):
    p = STUB / name; p.write_text("#!/bin/bash\n" + 'printf "%s\\x1f" "$(basename $0)" "$@" >> "$STUBLOG"; echo >> "$STUBLOG"\n' + body); p.chmod(0o755)
stub("curl", 'echo 203.0.113.7\n')
stub("sleep", 'exit 0\n')
stub("az", 'case "$*" in *"vm show"*) echo 198.51.100.9;; *"nsg list"*) echo nsg1;; *"rule list"*) echo ssh22;; esac\nexit 0\n')
stub("sshpass", 'shift 2; exec "$@"\n')
stub("rsync", 'exit 0\n')
stub("ssh", '[ "$SSH_DOWN" = 1 ] && exit 255\n'
     'case "$*" in *SSH_OK*) echo SSH_OK; echo mostafa;; '
     '*bendcore*) n=$(cat "$W/fpn" 2>/dev/null || echo 0); n=$((n+1)); echo $n > "$W/fpn"; '
     'if [ "$FP_CHANGE" = 1 ] && [ $n -ge 2 ]; then echo changed-state; else echo same-state; fi;; '
     '*curl*) echo 200;; esac\nexit 0\n')
def scenario(tag, cfg_text=None, args=(), env_extra=None, cfg_path=None):
    T = W / tag; inf = T / "workspace/shared/infra"; inf.mkdir(parents=True); (T / "workspace/shared/oth").mkdir(parents=True)
    (T / "workspace/shared/oth/.cred").write_text("azvmcred=dummy-pw\n")
    shutil.copy(dsh, inf / "deploy.sh")
    (inf / "deploy_changes.py").write_text("import pathlib;pathlib.Path(__file__).with_name('BASELINE_REDATED').write_text('x')\n")
    for d in ("src/b", "src/f"): (T / d).mkdir(parents=True)
    cfg = cfg_path or (W / f"{tag}.cfg")
    if cfg_text is not None: cfg.write_text(cfg_text.replace("$T", str(T)))
    log = W / f"{tag}.calls"; log.write_text("")
    env = {"PATH": f"{STUB}:/opt/homebrew/bin:/usr/bin:/bin", "HOME": str(W), "STUBLOG": str(log), "W": str(W),
           "ODIN_DEPLOY_CONFIG": str(cfg)}
    env.update(env_extra or {})
    (W / "fpn").unlink(missing_ok=True)
    r = subprocess.run(["bash", str(inf / "deploy.sh"), *args], env=env, capture_output=True, text=True, timeout=300)
    calls = [l.split("\x1f")[:-1] for l in log.read_text().splitlines() if l]
    return r, calls, (inf / "BASELINE_REDATED").exists()
SAND = '''CFG_BACKEND_LOCAL="$T/src/b"; CFG_BACKEND_VM="/home/mostafa/revealer-sandbox/b"; CFG_BACKEND_MIG="new"
CFG_FRONTEND_LOCAL="$T/src/f"; CFG_FRONTEND_VM="/home/mostafa/revealer-sandbox/f"; CFG_FRONTEND_MIG="none"
CFG_REBOOT=1
EXTRA_STEPS=( "echo sandbox-extra-step" )
'''
J = lambda c: " ".join(c)
# S1 dry run
r, calls, base = scenario("dry", SAND, ["--dry-run"])
out = r.stdout
rs = [c for c in calls if c[0] == "rsync"]
check("1 dry run: rsync previews both targets with -n", len(rs) == 2 and all("-n" in c for c in rs), [J(c)[:120] for c in rs])
ufw = " ".join(J(c) for c in calls if c[0] == "az" and "run-command" in J(c))
check("2 dry run: ufw only replaces the single-IP SSH allow (no deny, no 80/443, no reload/reset)",
      ufw.count("allow from 203.0.113.7") == 1 and not re.search(r"ufw (deny|reset|disable|reload)|80/tcp|443/tcp", ufw), ufw[:300])
nsg = [c for c in calls if c[0] == "az" and "rule update" in J(c)]
check("3 dry run: the NSG SSH rule is replaced once, for the current IP", len(nsg) == 1 and "203.0.113.7/32" in J(nsg[0]))
sshc = [J(c) for c in calls if c[0] == "ssh"]
bad = [c for c in sshc if re.search(r"prisma|npm run build|sandbox-extra-step|systemctl +(restart|start|stop|reload|enable)|reboot", c)]
check("4 dry run: no build, migration, extra step, restart or reboot reaches the VM", not bad, bad)
check("5 dry run: each skipped change is logged as WOULD RUN", "WOULD RUN (vm, as mostafa)" in out and "WOULD RUN (vm): echo sandbox-extra-step" in out and "WOULD RUN (local): deploy_changes.py update" in out, out[-600:])
check("6 dry run: the baseline lists are NOT re-dated", not base)
check("7 RBO Staging fingerprint read before and after (read-only) and unchanged", sum("bendcore" in c for c in sshc) >= 2 and "RBO Staging unchanged" in out and "STOP" not in out, out[-400:])
# S3 SSH down
r, calls, _ = scenario("down", SAND, ["--dry-run"], {"SSH_DOWN": "1"})
check("8 SSH down: sshd is never enabled/restarted (shared service)", not any(re.search(r"systemctl|service ssh", J(c)) for c in calls if c[0] == "az"))
# S2 full sandbox, CFG_REBOOT=1 and no services
r, calls, _ = scenario("full", SAND, [])
check("9 full sandbox run: never reboots the shared VM", not any("reboot" in J(c) for c in calls if c[0] == "ssh") and "REFUSED" in r.stdout, r.stdout[-400:])
# S4 RBO target in config
r, calls, _ = scenario("rbo", SAND.replace("/home/mostafa/revealer-sandbox/b", "/home/mostafa/bendcore"), [])
check("10 an RBO Staging target is refused before anything runs", r.returncode == 2 and not calls and "STOP (R-DP)" in r.stdout, (r.returncode, len(calls), r.stdout[-300:]))
# S5 the copy's real deploy.config.sh (RBO staging services/paths)
r, calls, _ = scenario("realcfg", None, ["--dry-run"], cfg_path=iso / "workspace/shared/infra/deploy.config.sh")
check("11 the RBO deploy config is refused (even a dry run touches nothing)", r.returncode == 2 and not calls, (r.returncode, len(calls)))
# S6 RBO fingerprint changes mid-run
r, calls, _ = scenario("fpchg", SAND + 'CFG_RESTART_SERVICES=( "revealer-sandbox" )\nCFG_REBOOT=0\n', [], {"FP_CHANGE": "1"})
after_restart = [J(c) for c in calls if c[0] == "ssh" and "systemctl restart" in J(c)]
check("12 RBO fingerprint change: STOP, no restart, run fails", "STOP (R-DP)" in r.stdout and not after_restart and r.returncode != 0, (r.returncode, after_restart))
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
