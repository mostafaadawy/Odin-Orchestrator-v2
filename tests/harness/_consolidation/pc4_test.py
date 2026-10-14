#!/usr/bin/env python3
"""PC-4 test (no LLM, no network): secure phone approvals through the Anchor. The Anchor is the attacker here:
it may drop, replay, alter or forge anything it relays. python pc4_test.py <root>"""
import sys, os, pathlib, json, base64, time, secrets
root = pathlib.Path(sys.argv[1]).resolve(); os.chdir(root)
sys.path.insert(0, str(root / "server")); sys.path.insert(0, str(root / "orchestrator"))
fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
try:
    import phone_approvals as pa, key_relay as kr, approvals, api_v2, local_poller_http as lp
except Exception as e:
    check("0: the PC-4 module exists", False, repr(e)); print("\nRESULT:", f"{len(fails)} FAIL: {fails}"); sys.exit(1)
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
for p in (pa.DEVICES, pa.NONCES, kr.SEEN):
    if p.exists(): p.unlink()
R = {(r.path, list(r.methods)[0]): r.endpoint for r in api_v2.build_router().routes if hasattr(r, "endpoint")}
def raw_pub(sk): return base64.b64encode(sk.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()
relay = kr.public_info()
phone = Ed25519PrivateKey.generate(); DEV = "iphone-" + secrets.token_hex(4); PUB = raw_pub(phone)
proof = base64.b64encode(phone.sign(pa.pair_message(DEV, PUB))).decode()

# --- pairing
d = pa.request_pairing(DEV, "Owner iPhone", PUB, proof)
check("1: pairing request is stored PENDING (nothing trusted yet)", d["status"] == "pending" and d["fingerprint"].count("-") == 3)
bad = Ed25519PrivateKey.generate()
try: pa.request_pairing("evil-1", "x", raw_pub(bad), proof); ok = False
except pa.PhoneApprovalError: ok = True
check("2: a pairing request without proof of the private key is refused", ok)
a = approvals.create("pc4-proj", "Backend", "Edit config", "change one line",
                     files=[{"path": "src/app.py", "action": "edit", "why": "fix", "preview": "print('v2')\n"}],
                     commands=[{"cmd": "pytest -q", "where": "local", "why": "verify"}])
view = pa.phone_view(approvals.get(a["id"]))
now = int(time.time())
env = pa.phone_sign_and_seal(phone, DEV, relay["pub"], view, "approve", secrets.token_hex(12), now)
try: pa.verify_decision(a["id"], env, approvals.get(a["id"])); ok = False
except pa.PhoneApprovalError as e: ok = "trust" in str(e)
check("3: a PENDING (not yet trusted) phone cannot decide", ok)
# the poller/Anchor path cannot trust a phone: no command kind for it
check("4: trusting a phone is NOT reachable through the Anchor (no poller command)", "phone_trust" not in open(root / "server/local_poller_http.py").read())
t = R.get(("/secrets/phone-devices/{device_id}/trust", "POST"))
check("5: the desktop trust route exists", t is not None)
r = t(DEV, {"channel": "desktop"}) if t else {}
check("6: owner trusts the phone on the desktop", (r or {}).get("status") == "trusted", r)

# --- a valid decision applies through the normal path, recorded as owner/phone
dec = R.get(("/approvals/{aid}/decide-e2e", "POST"))
check("7: the e2e decision route exists", dec is not None)
env = pa.phone_sign_and_seal(phone, DEV, relay["pub"], view, "approve", secrets.token_hex(12), int(time.time()))
import threading
_t = threading.Thread
class _NoThread:   # do not execute the approved change in the background during the test
    def __init__(self, *a, **k): pass
    def start(self): pass
threading.Thread = _NoThread
res = dec(a["id"], {"envelope": env})
threading.Thread = _t
after = approvals.get(a["id"])
check("8: valid signed+sealed decision is applied (approved)", after["status"] == "approved", res)
check("9: recorded as owner via phone (F-45) with the device id", after.get("decided_by") == "owner" and after.get("decided_channel") == "phone"
      and DEV in json.dumps(after.get("decisions", [])), after.get("decisions"))
# --- replay the SAME envelope
res2 = dec(a["id"], {"envelope": env})
check("10: replaying the same envelope is refused", "error" in (res2 or {}), res2)

# --- fresh pending request for the attack cases
def fresh(title="Second change"):
    x = approvals.create("pc4-proj", "Backend", title, "s", files=[{"path": "a.txt", "action": "create", "preview": "A"}])
    return x, pa.phone_view(approvals.get(x["id"]))
b, bv = fresh()
# (a) Anchor alters the decision inside: impossible without the Mac key; it swaps in its own sealed forgery
forger = Ed25519PrivateKey.generate()
env_f = pa.phone_sign_and_seal(forger, DEV, relay["pub"], bv, "approve", secrets.token_hex(12), int(time.time()))
r = dec(b["id"], {"envelope": env_f})
check("11: a decision signed by any other key is refused (Anchor forgery)", "error" in r and approvals.get(b["id"])["status"] == "pending", r)
# (b) the phone saw an altered request (Anchor changed the file content in the mirror)
bv2 = json.loads(json.dumps(bv)); bv2["files"][0]["preview"] = "rm -rf ~"
env_x = pa.phone_sign_and_seal(phone, DEV, relay["pub"], bv2, "approve", secrets.token_hex(12), int(time.time()))
r = dec(b["id"], {"envelope": env_x})
check("12: a decision on an ALTERED view of the request is refused (digest)", "error" in r and "digest" in r.get("error", ""), r)
# (c) the request changed on the Mac after the phone saw it
env_ok = pa.phone_sign_and_seal(phone, DEV, relay["pub"], bv, "approve", secrets.token_hex(12), int(time.time()))
items = approvals._all()
for it in items:
    if it["id"] == b["id"]: it["summary"] = "changed after the phone looked"
approvals._save(items)
r = dec(b["id"], {"envelope": env_ok})
check("13: tied to one request state: changed request -> refused", "error" in r and approvals.get(b["id"])["status"] == "pending", r)
# (d) moved to ANOTHER request id (AAD binds the id)
c, cv = fresh("Third change")
env_b = pa.phone_sign_and_seal(phone, DEV, relay["pub"], cv, "approve", secrets.token_hex(12), int(time.time()))
r = dec(b["id"], {"envelope": env_b})
check("14: an envelope for request C cannot approve request B", "error" in r and approvals.get(b["id"])["status"] == "pending", r)
# (e) expired
env_old = pa.phone_sign_and_seal(phone, DEV, relay["pub"], cv, "approve", secrets.token_hex(12), int(time.time()) - 3600)
r = dec(c["id"], {"envelope": env_old})
check("15: a decision older than the window is refused", "error" in r and "expired" in r.get("error", ""), r)
# (f) nonce reuse with a NEW envelope (re-sealed) is still refused
n = secrets.token_hex(12)
e1 = pa.phone_sign_and_seal(phone, DEV, relay["pub"], cv, "reject", n, int(time.time()))
r1 = dec(c["id"], {"envelope": e1})
check("16: a valid REJECT applies", approvals.get(c["id"])["status"] == "rejected", r1)
d2, dv2 = fresh("Fourth change")
e2 = pa.phone_sign_and_seal(phone, DEV, relay["pub"], dv2, "approve", n, int(time.time()))
r2 = dec(d2["id"], {"envelope": e2})
check("17: a reused nonce is refused even in a new envelope", "error" in r2, r2)
# (g) key requests never through Approve
k = approvals.create("pc4-proj", "Backend", "Need API key", "x", kind="key_request")
kv = pa.phone_view(approvals.get(k["id"]))
r = dec(k["id"], {"envelope": pa.phone_sign_and_seal(phone, DEV, relay["pub"], kv, "approve", secrets.token_hex(12), int(time.time()))})
check("18: key requests cannot be approved from the phone (F-41 secure field only)", "error" in r and approvals.get(k["id"])["status"] == "pending", r)
# (h) a plain (unsealed) decision is refused
r = dec(d2["id"], {"decision": "approve", "device_id": DEV})
check("19: an unsealed decision is refused", "error" in r and approvals.get(d2["id"])["status"] == "pending", r)
# (i) revoked phone
rv = R.get(("/secrets/phone-devices/{device_id}/revoke", "POST"))
rv(DEV, {"channel": "desktop"})
r = dec(d2["id"], {"envelope": pa.phone_sign_and_seal(phone, DEV, relay["pub"], dv2, "approve", secrets.token_hex(12), int(time.time()))})
check("20: a REVOKED phone cannot decide", "error" in r and approvals.get(d2["id"])["status"] == "pending", r)
# (j) re-pair with a NEW key does not inherit trust
p2 = Ed25519PrivateKey.generate(); P2 = raw_pub(p2)
s = pa.request_pairing(DEV, "Owner iPhone", P2, base64.b64encode(p2.sign(pa.pair_message(DEV, P2))).decode())
check("21: a new key for a known device id is PENDING again (never inherits trust)", s["status"] == "pending")
# --- the Anchor only ever sees ciphertext; mirror carries no secret
txt = json.dumps(env)
check("22: the relayed envelope carries no plaintext decision fields", all(w not in txt for w in ("approve", DEV, "digest")))
check("23: poller forwards the e2e decision and the pairing request as commands", "approval_e2e" in open(root / "server/local_poller_http.py").read()
      and "phone_pair" in open(root / "server/local_poller_http.py").read())
g = R.get(("/approvals", "GET"))
rows = g(pid="", all=0, kind="", phone=1)["approvals"] if g else []
check("24: the phone list excludes key requests and carries the full content the digest covers",
      rows and all(x.get("kind") != "key_request" for x in rows) and all("files" in x and "commands" in x for x in rows), rows[:1])
check("25: the mirrored phone list never exposes a stored secret (no 'value' field)", all("value" not in x for x in rows))
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}")
