#!/usr/bin/env python3
"""CUTOVER STEP 4 guard (owner condition D). READ-ONLY on RBO. usage:
   python 04a_vm_guard.py plan        -> prints exactly what the deploy touches (from the deploy code), nothing runs
   python 04a_vm_guard.py before      -> RBO fingerprint BEFORE + backup of the Odin folders/unit/DB on the VM itself
   python 04a_vm_guard.py after       -> RBO fingerprint AFTER, compared with BEFORE (must be identical)
RBO Staging = ~/bendcore (backend) + ~/organics (frontend) + their services/processes/ports/nginx sites. The fingerprint is
file paths+sizes+mtimes (hashed), service states, listening ports and nginx config hashes. Never prints a secret."""
import sys, json, time, hashlib, pathlib
V2 = pathlib.Path(__file__).resolve().parents[2]; sys.path.insert(0, str(V2 / "server"))
OUT = V2 / "_v2" / "cutover"
TOUCH = {
  "VM folders written (rsync --delete into)": ["/home/mostafa/anchor-online  (keeps .venv and anchor.log)",
                                                "/home/mostafa/odin-web       (keeps _serve_nocache.py and web.log)"],
  "VM files written": ["/etc/systemd/system/odin-anchor-online.service.d/pg.conf", "/tmp/odin/pg.conf (temporary, removed)",
                        "/home/mostafa/anchor-online/.venv (pip install psycopg2-binary)",
                        "/home/mostafa/odin_backups/<timestamp>/ (this guard's backup)"],
  "services": ["systemctl daemon-reload (re-reads unit files; restarts nothing)",
               "odin-anchor-online: stop / reset-failed / start", "odin-web-online: restart",
               "pkill -f 'anchor-online/anchor_remote.py' (only that file)"],
  "PostgreSQL (shared server, one role + one DB)": ["role odin_anchor: create if missing, new password",
                                                   "database odin_anchor: owner + grant to odin_anchor (never recreated)"],
  "firewall": ["the single dynamic-IP SSH rule refreshed to your current IP (replace, never add/open anything else)"],
  "read-only checks": ["nginx -t, ufw status, curl https://anchor.odinmarkets.com/odin-anchor/health and /odin-web"],
  "NOT touched": ["~/bendcore, ~/organics, their services, ports, databases, nginx sites; ports 80/443 rules; nginx reload"],
}
RBO_FP = r"""
set +e
for d in $HOME/bendcore $HOME/organics; do
  if [ -d "$d" ]; then echo "DIR $d $(find "$d" -path '*/node_modules' -prune -o -path '*/.git' -prune -o -type f -printf '%P %s %T@\n' 2>/dev/null | sort | sha256sum | cut -c1-16) files=$(find "$d" -path '*/node_modules' -prune -o -type f -print 2>/dev/null | wc -l)"; else echo "DIR $d missing"; fi
done
systemctl list-units --all --type=service --no-legend 2>/dev/null | grep -Ei 'bendcore|organics|rbo|redberry' | awk '{print "SVC",$1,$3,$4}'
for s in $(systemctl list-units --all --type=service --no-legend 2>/dev/null | grep -Ei 'bendcore|organics|rbo|redberry' | awk '{print $1}'); do echo "SVCPID $s $(systemctl show -p MainPID --value $s) since=$(systemctl show -p ActiveEnterTimestamp --value $s | tr ' ' '_')"; done
command -v pm2 >/dev/null && pm2 jlist 2>/dev/null | python3 -c "import sys,json;[print('PM2',p['name'],p['pm2_env']['status'],p['pid'],p['pm2_env'].get('pm_uptime')) for p in json.load(sys.stdin)]" 2>/dev/null
ss -ltn 2>/dev/null | awk 'NR>1{print "PORT",$4}' | grep -vE ':4861[0-9]$|:4862[0-9]$|:22$' | sed -E 's/pid=[0-9]+,fd=[0-9]+//g' | sort -u
for f in /etc/nginx/sites-enabled/*; do echo "NGINX $f $(sha256sum "$f" 2>/dev/null | cut -c1-16)"; done
sudo -u postgres psql -Atc "select 'DB '||datname from pg_database where datname not in ('odin_anchor','template0','template1','postgres') order by 1" 2>/dev/null
"""
BACKUP = r"""
set -e
B=/home/mostafa/odin_backups/$(date +%Y%m%d_%H%M%S); mkdir -p $B; chmod 700 /home/mostafa/odin_backups $B
[ -d /home/mostafa/anchor-online ] && tar -C /home/mostafa --exclude=anchor-online/.venv --exclude="anchor-online/.cred*" -czf $B/anchor-online.tgz anchor-online
[ -d /home/mostafa/odin-web ] && tar -C /home/mostafa -czf $B/odin-web.tgz odin-web
sudo cp -p /etc/systemd/system/odin-anchor-online.service.d/pg.conf $B/pg.conf 2>/dev/null || true
sudo -u postgres pg_dump -Fc odin_anchor > $B/odin_anchor_vm.dump 2>/dev/null || true
sudo chown -R mostafa: $B; chmod 600 $B/* 2>/dev/null; echo "VMBACKUP $B $(ls $B | tr '\n' ' ')"
"""
def ssh():
    import deploy_ssh
    deploy_ssh.refresh_firewall()
    return deploy_ssh
def run(d, cmd):
    r = d.ssh_exec(cmd, timeout=600)
    return (r.get("out") or ""), r.get("ok", False)
def strip_vol(lines):   # PIDs/ports of RBO must not change; the anchor's own lines are excluded above
    return sorted(l for l in lines if l.strip())
mode = sys.argv[1] if len(sys.argv) > 1 else "plan"
if mode == "plan":
    for k, v in TOUCH.items():
        print(k); [print("   -", x) for x in v]
    sys.exit(0)
d = ssh()
out, ok = run(d, RBO_FP)
fp = strip_vol(out.splitlines())
if mode == "before":
    (OUT / "rbo_fp_before.json").write_text(json.dumps(fp, indent=1))
    print(f"RBO fingerprint BEFORE: {len(fp)} items"); [print("  ", l) for l in fp if not l.startswith("PORT")]
    if "--no-backup" in sys.argv: sys.exit(0)
    b, ok2 = run(d, BACKUP); print(b.strip().splitlines()[-1] if b.strip() else "VM backup: no output"); sys.exit(0 if ok2 else 1)
if mode == "after":
    before = json.loads((OUT / "rbo_fp_before.json").read_text())
    (OUT / "rbo_fp_after.json").write_text(json.dumps(fp, indent=1))
    gone = [l for l in before if l not in fp]; new = [l for l in fp if l not in before]
    if not gone and not new:
        print(f"✓ RBO UNTOUCHED: all {len(fp)} fingerprint items identical (files, services, PIDs, ports, nginx sites, DBs)"); sys.exit(0)
    print("❌ RBO FINGERPRINT CHANGED — STOP"); [print("   before:", l) for l in gone]; [print("   after: ", l) for l in new]; sys.exit(1)
