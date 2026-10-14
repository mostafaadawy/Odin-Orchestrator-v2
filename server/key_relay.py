"""F-41 — end-to-end encrypted key relay (phone -> Anchor -> Mac).

The phone reaches the Mac only through the Anchor (VM). A key must never transit or rest there in plain form, so:
  1. the Mac (this brain) owns an X25519 key pair; only the PUBLIC key leaves (mirrored to the Anchor);
  2. the phone pins the Mac's key fingerprint (trust-on-first-use) and seals the key value to it:
       ephemeral X25519 -> HKDF-SHA256 -> AES-256-GCM, AAD binds the approval id and the key name;
  3. the Anchor relays only the sealed envelope (ciphertext) as an ordinary command;
  4. the Mac opens it here and hands the value to secret_store.provide_key (same path as the desktop field).
Envelope: {"v":1,"alg":ALG,"kid":..,"epk":b64,"nonce":b64,"ct":b64}. Values are never logged or returned.
The private key lives in data/relay_x25519.json (gitignored, mode 600); F-14 Keychain storage is a later option."""
from __future__ import annotations
import base64, hashlib, json, os, pathlib, tempfile, threading, time

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes, serialization

ALG = "X25519-HKDF-SHA256-AES256GCM-v1"
INFO = b"odin-key-relay-v1"
ROOT = pathlib.Path(__file__).resolve().parent.parent
KEYFILE = ROOT / "data" / "relay_x25519.json"
SEEN = ROOT / "data" / "relay_seen.json"
MAX_AGE = 3600 * 24 * 30
_LOCK = threading.Lock()


def _b64e(b: bytes) -> str: return base64.b64encode(b).decode()
def _b64d(s: str) -> bytes: return base64.b64decode(s.encode(), validate=True)
def _raw(pub: X25519PublicKey) -> bytes:
    return pub.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
def kid_of(pub_raw: bytes) -> str: return hashlib.sha256(pub_raw).hexdigest()[:16]


def _atomic_write(p: pathlib.Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix="." + p.name + ".")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.chmod(tmp, 0o600)
    os.replace(tmp, p)


def _private() -> X25519PrivateKey:
    with _LOCK:
        if KEYFILE.exists():
            d = json.loads(KEYFILE.read_text())
            return X25519PrivateKey.from_private_bytes(_b64d(d["sk"]))
        sk = X25519PrivateKey.generate()
        raw = sk.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
                               serialization.NoEncryption())
        _atomic_write(KEYFILE, json.dumps({"alg": ALG, "sk": _b64e(raw), "created": int(time.time())}))
        return sk


def public_info() -> dict:
    """What the phone needs: the public key and its fingerprint. Never the private key."""
    pub = _raw(_private().public_key())
    return {"alg": ALG, "pub": _b64e(pub), "kid": kid_of(pub)}


def aad(aid: str, name: str) -> bytes:
    return f"odin-key-relay|v1|{aid}|{(name or '').strip().upper()}".encode()


def _derive(shared: bytes, epk: bytes, pub: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=epk + pub, info=INFO).derive(shared)


def seal(pub_b64: str, value: str, aid: str, name: str) -> dict:
    """Reference sealer (what the phone does). Used by tests."""
    pub = _b64d(pub_b64)
    esk = X25519PrivateKey.generate(); epk = _raw(esk.public_key())
    k = _derive(esk.exchange(X25519PublicKey.from_public_bytes(pub)), epk, pub)
    nonce = os.urandom(12)
    ct = AESGCM(k).encrypt(nonce, value.encode("utf-8"), aad(aid, name))
    return {"v": 1, "alg": ALG, "kid": kid_of(pub), "epk": _b64e(epk), "nonce": _b64e(nonce), "ct": _b64e(ct)}


class RelayError(ValueError):
    pass


def _seen_check_and_add(tag: str) -> bool:
    """Replay guard: each envelope (by its ephemeral key) may be opened once."""
    with _LOCK:
        try:
            seen = json.loads(SEEN.read_text()) if SEEN.exists() else {}
        except Exception:
            seen = {}
        now = int(time.time())
        seen = {k: v for k, v in seen.items() if now - int(v) < MAX_AGE}
        if tag in seen:
            return False
        seen[tag] = now
        _atomic_write(SEEN, json.dumps(seen))
        return True


def open_envelope(env: dict, aid: str, name: str) -> str:
    """Open a sealed envelope for approval `aid` / key `name`. Raises RelayError (no detail about the value)."""
    if not isinstance(env, dict) or env.get("v") != 1 or env.get("alg") != ALG:
        raise RelayError("unsupported envelope")
    sk = _private(); pub = _raw(sk.public_key())
    if env.get("kid") != kid_of(pub):
        raise RelayError("envelope was sealed to a different Mac key (fingerprint mismatch)")
    try:
        epk = _b64d(env["epk"]); nonce = _b64d(env["nonce"]); ct = _b64d(env["ct"])
    except Exception:
        raise RelayError("malformed envelope")
    if len(epk) != 32 or len(nonce) != 12:
        raise RelayError("malformed envelope")
    k = _derive(sk.exchange(X25519PublicKey.from_public_bytes(epk)), epk, pub)
    try:
        pt = AESGCM(k).decrypt(nonce, ct, aad(aid, name))
    except Exception:
        raise RelayError("envelope does not open (tampered, or bound to another request)")
    if not _seen_check_and_add(hashlib.sha256(epk).hexdigest()):
        raise RelayError("envelope already used (replay)")
    return pt.decode("utf-8")
