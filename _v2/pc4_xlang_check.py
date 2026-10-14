"""PC-4 cross-language check: the Dart phone's sealed+signed decision opens and verifies with the Python Mac code.
usage: (cd <root> && python pc4_xlang_check.py <root> <pc4_out.json>)"""
import sys, json, base64, pathlib
root = pathlib.Path(sys.argv[1]); sys.path.insert(0, str(root / "server"))
import key_relay as kr, phone_approvals as pa
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
d = json.loads(open(sys.argv[2]).read()); a = d["approval"]
inner = json.loads(kr.open_envelope(d["envelope"], a["id"], pa.ENVELOPE_NAME))
ok_dg = inner["digest"] == pa.digest(a)
Ed25519PublicKey.from_public_bytes(base64.b64decode(d["pub"])).verify(
    base64.b64decode(inner["sig"]), pa.sig_message(a["id"], inner["decision"], inner["digest"], inner["nonce"], inner["ts"], inner["device_id"]) + b"|" + inner["note"].encode())
print("XLANG", "OK" if ok_dg and inner["decision"] == "approve" else "FAIL", "digest_match=", ok_dg)
