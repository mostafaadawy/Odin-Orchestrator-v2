#!/usr/bin/env python3
"""Step F / F-41 relay test (no LLM). python stepF_test.py <root> [dart_envelope.json]
The phone seals a key to the Mac's public key; the Anchor carries only ciphertext; the Mac opens and stores it."""
import sys, os, pathlib, json, base64, stat, copy
root = pathlib.Path(sys.argv[1]).resolve(); os.chdir(root); sys.path.insert(0, str(root / "server"))
dart_env = sys.argv[2] if len(sys.argv) > 2 else ""
fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
import projects, secret_store, api_v2, approvals
try:
    import key_relay
except Exception as e:
    check("1: the Mac has a relay key module", False, repr(e)); print("\nRESULT:", f"{len(fails)} FAIL: {fails}"); sys.exit(1)
R = {(r.path, list(r.methods)[0]): r.endpoint for r in api_v2.build_router().routes if hasattr(r, "endpoint")}
CRED = root / "workspace/shared/oth/.cred"
def cred_has(v): return CRED.exists() and v in CRED.read_text()
pk = R.get(("/secrets/relay-pubkey", "GET"))
info = pk() if pk else {}
check("1: GET /secrets/relay-pubkey gives pub + kid only (no private key)", set(info) == {"alg", "pub", "kid"} and len(base64.b64decode(info["pub"])) == 32, info)
kf = key_relay.KEYFILE
check("2: the private key is stored under data/ with mode 600", kf.exists() and stat.S_IMODE(kf.stat().st_mode) == 0o600 and "data" in kf.parts)
p = projects.create_project("F41R Shop", "shop", members=[{"name": "Email", "role": "Email"}], identifier="f41r-shop")
a = secret_store.request_key(p["id"], "Email", "klaviyo", "KLAVIYO_KEY_F41R", "test")
VAL = "sk-relay-VALUE-7781"
env = key_relay.seal(info["pub"], VAL, a["id"], "KLAVIYO_KEY_F41R")
blob = json.dumps(env)
check("3: the envelope (what the Anchor sees) contains no plaintext", VAL not in blob and base64.b64encode(VAL.encode()).decode() not in blob)
e2e = R.get(("/secrets/project-key-e2e", "POST"))
check("4: plain value on the relay path is refused", e2e is not None and e2e({"aid": a["id"], "value": VAL}).get("ok") is False and not cred_has(VAL))
bad = copy.deepcopy(env); ct = bytearray(base64.b64decode(bad["ct"])); ct[0] ^= 1; bad["ct"] = base64.b64encode(bytes(ct)).decode()
r = e2e({"aid": a["id"], "envelope": bad}) if e2e else {}
check("5: a tampered envelope is refused, nothing stored", r.get("ok") is False and not cred_has(VAL), r)
a2 = secret_store.request_key(p["id"], "Email", "klaviyo", "OTHER_KEY_F41R", "test")
r = e2e({"aid": a2["id"], "envelope": env}) if e2e else {}
check("6: an envelope bound to another request is refused", r.get("ok") is False and VAL not in json.dumps(r), r)
wk = dict(env, kid="0000000000000000")
r = e2e({"aid": a["id"], "envelope": wk}) if e2e else {}
check("7: an envelope for a different Mac key is refused", r.get("ok") is False and "fingerprint" in r.get("error", ""), r)
# the poller relays the sealed command (as the Anchor would hand it over)
import local_poller_http as lp
lp._brain_post = lambda path, body: R[(path, "POST")](body)
reply = lp._run_command({"payload": {"kind": "key_e2e", "aid": a["id"], "name": "KLAVIYO_KEY_F41R", "envelope": env}})
st = approvals.get(a["id"])
check("8: the poller's key_e2e command stores the key on the Mac", cred_has(VAL) and st.get("status") != "pending", reply)
check("9: the poller reply never contains the value", VAL not in reply and "stored" in reply, reply)
dec = (st.get("decisions") or [{}])[-1]
check("10: the approval records owner via phone", st.get("decided_by") == "owner" and st.get("decided_channel") == "phone", dec)
try:
    key_relay.open_envelope(env, a["id"], "KLAVIYO_KEY_F41R"); rep = False
except key_relay.RelayError as e:
    rep = "replay" in str(e)
check("11: the same envelope cannot be opened twice (replay)", rep)
src = (root / "server/local_poller_http.py").read_text()
check("12: the poller mirrors relay_pubkey and ONLY key requests", '"/secrets/relay-pubkey"' in src and '"/approvals?kind=key_request"' in src and '("approvals", "/approvals")' not in src)
secret_store.request_key(p["id"], "Email", "klaviyo", "THIRD_KEY_F41R", "test")
approvals.create(p["id"], "Email", title="normal change", summary="x", kind="change") if "kind" in approvals.create.__code__.co_varnames else None
rows = R[("/approvals", "GET")](p["id"], 0, "key_request")["approvals"]
check("13: /approvals?kind=key_request lists key requests only (what the Anchor gets)", rows and all(x.get("kind") == "key_request" for x in rows) and all(x.get("relay") for x in rows), [x.get("kind") for x in rows])
if dart_env and os.path.exists(dart_env):
    denv = json.loads(open(dart_env).read())
    try:
        got = key_relay.open_envelope(denv, "f41-xlang", "XLANG_KEY"); ok = got == "sk-xlang-SECRET-42"
    except Exception as e:
        ok = False; got = repr(e)
    check("14: an envelope sealed by the PHONE code (Dart) opens on the Mac (Python)", ok, "" if ok else got)
else:
    check("14: an envelope sealed by the PHONE code (Dart) opens on the Mac (Python)", False, "no Dart envelope")
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
