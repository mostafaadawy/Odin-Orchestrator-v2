#!/usr/bin/env python3
"""
Post-deploy STRONG VERIFICATION — the mandatory gate the DevOps agent runs after every organics deploy.
The deploy is NOT "done" until this prints VERDICT: ✅ PASS. It NEVER fakes success.

WHY (real incidents 2026-07-16):
  - `migrate reset --force` dropped every table under the still-running process; the deploy skipped the
    restart, so the boot self-seed never re-ran → DB EMPTY (users=0) yet the OLD process still answered
    HTTP 200 → "You do not have permission" on every login. HTTP 200 is NOT proof of a good deploy.
  - The health check curled the WRONG port (3000 instead of the real organics port 3001) and never checked
    the frontend BUILD_ID, so a STALE build (08:44, from before the deploy) passed as "healthy".

STRONG CHECKPOINTS (all over SSH as mostafa — never root, never touch nginx/ports, never `npm start`):
  1. REAL FILE CHANGE ON VM — backend `dist/` and frontend `.next/BUILD_ID` must be FRESH (rebuilt within
     the deploy window). A stale build fails. This proves the code actually changed on the VM.
  2. SMART ENDPOINTS — poll backend :4014 and frontend :3001 (the REAL organics port) to a real HTTP 200.
  3. DB HEALTH — users>0, rbacRoles>0, at least one isSuperadmin=true, appSettings seeded (captcha config).
  4. AUTO-REMEDIATE ONCE — if DB is empty but services are up, restart bendcore (boot self-seed refills),
     wait, re-check. (Restart after a reset is the step that re-runs the seed.)

  Ports are READ-ONLY here (curl only). This script never edits nginx, ports, or firewall.

    python infra/deploy_verify.py --since-epoch <ts>   # ts = unix time the deploy started (freshness bar)
    python infra/deploy_verify.py                      # freshness bar defaults to "within last 45 min"
    python infra/deploy_verify.py --no-fix             # verify only, do not auto-restart
"""
from __future__ import annotations
import sys, os, json, time, base64, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent.parent / "server"))
import deploy_ssh as d  # ssh_exec runs AS mostafa, auto-handles sudo -S with the password

BACKEND_URL   = "http://127.0.0.1:4014/"   # staging backend (bendcore-staging)
FRONTEND_URL  = "http://127.0.0.1:3001/"   # staging frontend (organics-staging)
BACKEND_DIR   = "/home/mostafa/RBO-Staging/b"
FRONTEND_DIR  = "/home/mostafa/RBO-Staging/f"
SERVICE_BE    = "bendcore-staging"

DB_CHECK_JS = r'''
const{PrismaClient}=require('@prisma/client');const p=new PrismaClient();
(async()=>{const o={};
 const q=async(n,f)=>{try{o[n]=await f()}catch(e){o[n]='ERR:'+(e.message||'').split("\n")[0]}};
 await q('users',()=>p.user.count());
 await q('rbacRoles',()=>p.rbacRole.count());
 await q('superadmins',()=>p.user.count({where:{isSuperadmin:true}}));
 await q('appSettings',()=>p.appSetting.count());
 console.log('DBJSON'+JSON.stringify(o));
 await p.$disconnect();})().catch(e=>{console.log('DBJSON{"fatal":"'+String(e.message).replace(/"/g,'')+'"}')});
'''


def _mtime(path: str) -> int:
    r = d.ssh_exec(f"stat -c '%Y' {path} 2>/dev/null || echo 0")
    try:
        return int((r.get("out") or "0").strip().split()[-1])
    except Exception:
        return 0


def _poll_http(url: str, tries: int = 18, gap: int = 10) -> int:
    last = 0
    for _ in range(tries):
        r = d.ssh_exec(f"curl -s -o /dev/null -w '%{{http_code}}' --max-time 8 {url}")
        try:
            last = int((r.get("out") or "").strip()[-3:])
        except Exception:
            last = 0
        if last == 200:
            return 200
        time.sleep(gap)
    return last


def _db_health() -> dict:
    b64 = base64.b64encode(DB_CHECK_JS.encode()).decode()
    r = d.ssh_exec(f"cd {BACKEND_DIR} && echo {b64} | base64 -d | node 2>&1 | grep DBJSON | tail -1")
    out = (r.get("out") or "").strip()
    i = out.find("DBJSON")
    if i < 0:
        return {"_raw": out or "no output"}
    try:
        return json.loads(out[i + 6:])
    except Exception:
        return {"_raw": out}


def _db_ok(h: dict) -> bool:
    def n(k):
        v = h.get(k); return v if isinstance(v, int) else -1
    return n("users") > 0 and n("rbacRoles") > 0 and n("superadmins") > 0 and n("appSettings") > 0


def main(since_epoch: int, fix: bool = True) -> int:
    print("== POST-DEPLOY STRONG VERIFY ==")
    print(f"  freshness bar: builds must be newer than {time.strftime('%H:%M:%S', time.localtime(since_epoch))} "
          f"(deploy window)")

    # 1) REAL FILE CHANGE ON VM (build freshness) — proves the code actually redeployed
    dist_m = _mtime(f"{BACKEND_DIR}/dist")
    bid_m  = _mtime(f"{FRONTEND_DIR}/.next/BUILD_ID")
    be_fresh = dist_m >= since_epoch
    fe_fresh = bid_m  >= since_epoch
    print(f"  backend  dist  mtime={time.strftime('%H:%M:%S', time.localtime(dist_m)) if dist_m else 'MISSING'}  "
          f"{'FRESH ✓' if be_fresh else 'STALE ✗'}")
    print(f"  frontend BUILD_ID mtime={time.strftime('%H:%M:%S', time.localtime(bid_m)) if bid_m else 'MISSING'}  "
          f"{'FRESH ✓' if fe_fresh else 'STALE ✗'}")

    # 2) SMART ENDPOINTS (real organics port 3001)
    be = _poll_http(BACKEND_URL)
    fe = _poll_http(FRONTEND_URL)
    print(f"  endpoints: backend:4014={be}  frontend:3001={fe}")

    # 3) DB HEALTH
    h = _db_health()
    print(f"  db: {json.dumps(h)}")
    ok = _db_ok(h)

    # 4) AUTO-REMEDIATE ONCE (empty DB but service up → restart to trigger boot self-seed)
    if not ok and fix:
        print("  ✗ DB empty/partial — AUTO-REMEDIATE: restarting bendcore to trigger boot self-seed…")
        print("    " + (d.ssh_exec(f"sudo systemctl restart {SERVICE_BE} && echo RESTARTED").get("out") or "").strip())
        time.sleep(30)
        be = _poll_http(BACKEND_URL)
        h = _db_health(); ok = _db_ok(h)
        print(f"  after restart: backend={be}  db={json.dumps(h)}")

    endpoints_ok = (be == 200 and fe == 200)
    builds_ok = be_fresh and fe_fresh
    verdict = endpoints_ok and ok and builds_ok
    print("\nVERDICT:", "✅ PASS — real redeploy (fresh builds + endpoints 200 + DB seeded + superadmin present)"
          if verdict else
          "❌ FAIL — do NOT report success and do NOT update the change-lists. "
          + ("" if builds_ok else "build(s) STALE (code did not change on VM). ")
          + ("" if endpoints_ok else "endpoint(s) not 200. ")
          + ("" if ok else "DB empty/partial even after restart. "))
    return 0 if verdict else 1


if __name__ == "__main__":
    since = int(time.time()) - 45 * 60
    if "--since-epoch" in sys.argv:
        since = int(sys.argv[sys.argv.index("--since-epoch") + 1])
    sys.exit(main(since, fix=("--no-fix" not in sys.argv)))
