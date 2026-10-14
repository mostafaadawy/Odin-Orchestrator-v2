#!/bin/bash
# Proof (cutover check, credentials): run the Anchor exactly as deployed — ONE flat folder with the deploy file list and a
# DUMMY minimal .cred — record every credential NAME the code asks for at runtime, and check auth is enforced.
set -u
V2=$(cd "$(dirname "$0")/../.." && pwd); T=$HOME/odin_flat_test; rm -rf "$T"; mkdir -p "$T"; P=${PORT:-39931}
for f in $(python3 -c "import sys;sys.path.insert(0,'$V2/workspace/shared/infra');import phase3_gate as g;print(' '.join(g.ANCHOR_FILES))"); do
  mkdir -p "$T/$(dirname $f)"; cp "$V2/server/$f" "$T/$f"; done
printf 'ANCHOR_API_KEY=dummy_test_key_0123456789\nANCHOR_MANAGE_EMAIL=test@example.com\nANCHOR_MANAGE_PWSHA=%s\n' "$(python3 -c 'import hashlib;print(hashlib.sha256(b"x").hexdigest())')" > "$T/.cred"
cat > "$T/_trace.py" <<'PY'
import sys, runpy, json, os
D, PORT = sys.argv[1], sys.argv[2]
sys.path.insert(0, D)
import integrations.cred as c
_g = c.get
names = set()
def get(k, d=""):
    names.add(k)
    open(os.path.join(D, "_names.json"), "w").write(json.dumps(sorted(names)))
    return _g(k, d)
c.get = get
sys.argv = ["anchor_remote.py", "--host", "127.0.0.1", "--port", PORT]
runpy.run_path(os.path.join(D, "anchor_remote.py"), run_name="__main__")
PY
cd "$T"; perl -e 'alarm shift; exec @ARGV' 60 python3 -u _trace.py "$T" $P > run.log 2>&1 & SPID=$!; cd - >/dev/null; sleep 3
trap 'kill $SPID 2>/dev/null; wait $SPID 2>/dev/null' EXIT    # stop the test Anchor ourselves (no "Alarm clock")
K='X-API-Key: dummy_test_key_0123456789'; U=http://127.0.0.1:$P
echo "health auth_required: $(curl -s $U/health | python3 -c 'import sys,json;print(json.load(sys.stdin).get("auth_required"))')"
echo "no key   GET  mirror          -> $(curl -s -o /dev/null -w %{http_code} $U/anchor/v1/mirror/ui_projects)"
echo "with key GET  mirror          -> $(curl -s -o /dev/null -w %{http_code} -H "$K" $U/anchor/v1/mirror/ui_projects)"
echo "no key   POST command run_now -> $(curl -s -o /dev/null -w %{http_code} -X POST -H 'Content-Type: application/json' -d '{"project":"__command__","sender":"command","payload":{"kind":"run_now"}}' $U/anchor/v1/requests)"
curl -s -o /dev/null -X POST -H 'Content-Type: application/json' -d '{"email":"test@example.com","password":"x","code":""}' $U/anchor/v1/manage/login
curl -s -o /dev/null -H "$K" $U/anchor/v1/manage/pending-code
curl -s -o /dev/null -X POST -H "$K" -H 'Content-Type: application/json' -d '{}' $U/anchor/v1/manage/request-code
sleep 1; echo "credential NAMES read at runtime: $(cat $T/_names.json 2>/dev/null)"
grep -h "auth=" "$T/run.log" | head -1
# web/mobile: no API key; a Manage session (email + password + desktop code) is the only way in
curl -s -o /dev/null -X POST -H 'Content-Type: application/json' -d '{"target":"web"}' $U/anchor/v1/manage/request-code
CODE=$(curl -s -H "$K" "$U/anchor/v1/manage/pending-code?target=web" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("code") or (d.get("pending") or {}).get("code",""))')
TOK=$(curl -s -X POST -H 'Content-Type: application/json' -d "{\"email\":\"test@example.com\",\"password\":\"x\",\"code\":\"$CODE\",\"target\":\"web\"}" $U/anchor/v1/manage/login | python3 -c 'import sys,json;print(json.load(sys.stdin).get("token",""))')
W1=$(curl -s -o /dev/null -w %{http_code} -H 'X-Odin-Client: web' $U/anchor/v1/mirror/ui_projects)
W2=$(curl -s -o /dev/null -w %{http_code} -H 'X-Odin-Client: web' -H "X-Manage-Token: $TOK" $U/anchor/v1/mirror/ui_projects)
W3=$(curl -s -o /dev/null -w %{http_code} -H 'X-Odin-Client: web' -H 'X-Manage-Token: forged-token' $U/anchor/v1/mirror/ui_projects)
echo "web, no session -> $W1 ; web, real session (no key) -> $W2 ; web, forged session -> $W3"
N=$(cat $T/_names.json 2>/dev/null)
A=$(curl -s -o /dev/null -w %{http_code} $U/anchor/v1/mirror/ui_projects)
if [ "$N" = '["ANCHOR_API_KEY", "ANCHOR_MANAGE_EMAIL", "ANCHOR_MANAGE_PWSHA"]' ] && [ "$A" = 401 ] && [ "$W1" = 401 ] && [ "$W2" = 200 ] && [ "$W3" = 401 ]; then echo "FLAT ANCHOR OK"; else echo "FLAT ANCHOR FAILED"; exit 1; fi
