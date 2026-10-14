set +e
echo "== nginx config: what is web-served (root/alias) and where /odin-* go"
sudo grep -rnE "root |alias |location .*odin|proxy_pass" /etc/nginx/sites-enabled/ 2>/dev/null | grep -iE "odin|anchor|48619|48620|/home/mostafa" | sed 's/^/   /'
echo "== .cred copies inside web-served Odin folders:"; sudo find /home/mostafa/odin-web -name '.cred*' 2>/dev/null | sed 's/^/   /'; echo "   (end)"
echo "== web server for /odin-web:"; sudo systemctl cat odin-web-online 2>/dev/null | grep -E "ExecStart|WorkingDirectory" | sed 's/^/   /'
echo "== anchor service unit:"; sudo systemctl cat odin-anchor-online 2>/dev/null | grep -E "ExecStart|WorkingDirectory" | sed 's/^/   /'
echo "== first Odin deploy (anchor folder creation):"; stat -c '   anchor-online created/changed: %w / %y' /home/mostafa/anchor-online 2>/dev/null
ls /var/log/nginx/ | tr '\n' ' '; echo
sudo python3 - <<'PY'
import glob, gzip, re, collections, datetime
L = re.compile(r'^(\S+) \S+ \S+ \[([^\]]+)\] "(\S+) (\S+)[^"]*" (\d{3}) \S+ "[^"]*" "([^"]*)"')
files = sorted(glob.glob('/var/log/nginx/access.log*'))
ips = collections.defaultdict(lambda: {"n":0,"first":None,"last":None,"paths":collections.Counter(),"ua":collections.Counter(),"codes":collections.Counter()})
cred_hits = []; total = 0; oldest = None
for f in files:
    op = gzip.open if f.endswith('.gz') else open
    try:
        for line in op(f, 'rt', errors='replace'):
            m = L.match(line)
            if not m: continue
            ip, ts, meth, path, code, ua = m.groups()
            t = datetime.datetime.strptime(ts.split()[0], '%d/%b/%Y:%H:%M:%S')
            oldest = t if oldest is None or t < oldest else oldest
            p = path.split('?')[0]
            if '.cred' in path or 'oth/' in path:
                cred_hits.append((str(t), ip, meth, p, code))
            if not (p.startswith('/odin-anchor') or p.startswith('/odin-web')): continue
            total += 1; r = ips[ip]; r["n"] += 1
            r["first"] = t if r["first"] is None or t < r["first"] else r["first"]
            r["last"] = t if r["last"] is None or t > r["last"] else r["last"]
            seg = '/'.join(p.split('/')[:5]); r["paths"][meth + ' ' + seg] += 1; r["ua"][ua[:40]] += 1; r["codes"][code] += 1
    except Exception as e:
        print('   could not read', f, e)
print("== logs cover from", oldest, "| Odin requests:", total, "| distinct IPs:", len(ips))
for ip, r in sorted(ips.items(), key=lambda x: -x[1]["n"]):
    print(f"IP {ip}  n={r['n']}  {r['first']} .. {r['last']}  codes={dict(r['codes'])}")
    print("     ua:", "; ".join(f"{u} x{c}" for u, c in r['ua'].most_common(3)))
    print("     paths:", "; ".join(f"{p} x{c}" for p, c in r['paths'].most_common(6)))
print("== requests for .cred / oth/ anywhere on the server:", len(cred_hits))
for h in cred_hits[:40]: print("   ", h)
PY
echo "== anchor.log size/dates:"; ls -la /home/mostafa/anchor-online/anchor.log 2>/dev/null; head -1 /home/mostafa/anchor-online/anchor.log 2>/dev/null | cut -c1-120
