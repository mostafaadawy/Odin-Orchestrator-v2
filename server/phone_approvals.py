"""PC-4 — secure phone approvals through the Anchor (owner 2026-10-12, D-1: REQUIRED before cutover).

The phone reaches the Mac only through the Anchor (VM), which is treated as UNTRUSTED. A phone decision is accepted
only if ALL of these hold:
  1. the phone is PAIRED: its Ed25519 public key was registered and the owner TRUSTED it on the desktop after
     comparing the fingerprint shown on both screens (the Anchor cannot swap the key unnoticed);
  2. the decision is SIGNED by that phone key (the Anchor cannot forge or alter a decision);
  3. the signature covers a DIGEST of the exact approval the phone showed (id, project, kind, title, summary, cwd,
     every file action/path/content and every command) — the Mac recomputes it from ITS record, so a decision is
     tied to ONE request in ONE state (if the request changed, the decision is refused);
  4. it is SEALED to the Mac's relay key (F-41 envelope, AAD bound to the approval id) — the Anchor sees ciphertext;
  5. it is FRESH and used ONCE: timestamp window + one-time nonce + the envelope's own replay guard;
  6. it is for a PENDING request of a kind the phone may decide (never a key request — those use the F-41 secure
     field; never a bulk "approve all").
Decisions are recorded with who=owner and channel=phone, plus the device id (F-45 history).
Stored: data/phone_devices.json (public keys + status), data/phone_nonces.json (used nonces). No secret is stored here.
"""
from __future__ import annotations

import base64
import hashlib
import json
import pathlib
import threading
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

import key_relay

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEVICES = ROOT / "data" / "phone_devices.json"
NONCES = ROOT / "data" / "phone_nonces.json"
WINDOW_S = 15 * 60          # a signed decision is valid for 15 minutes
FUTURE_SKEW_S = 120         # tolerate a phone clock up to 2 minutes ahead
NONCE_KEEP_S = 2 * 24 * 3600
ENVELOPE_NAME = "APPROVAL"  # F-41 AAD name for approval envelopes
PHONE_KINDS_EXCLUDED = ("key_request",)
_LOCK = threading.Lock()


class PhoneApprovalError(ValueError):
    pass


def _h(s) -> str:
    return hashlib.sha256(("" if s is None else str(s)).encode("utf-8")).hexdigest()


def digest(a: dict) -> str:
    """The exact content the owner approves. Every field is hashed on its own (no separator ambiguity).
    The phone computes the SAME value from what it shows (odin_app/lib/security/phone_approval.dart)."""
    files = [_h(f.get("action", "")) + ":" + _h(f.get("path", "")) + ":" + _h(f.get("preview", ""))
             for f in (a.get("files") or []) if isinstance(f, dict)]
    cmds = [_h(c.get("where", "")) + ":" + _h(c.get("cmd", "")) for c in (a.get("commands") or []) if isinstance(c, dict)]
    parts = ["odin-approval", "v1", str(a.get("id", "")), _h(a.get("pid", "")), _h(a.get("kind", "")),
             _h(a.get("title", "")), _h(a.get("summary", "")), _h(a.get("cwd", "")),
             _h("\n".join(files)), _h("\n".join(cmds))]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def sig_message(aid: str, decision: str, dg: str, nonce: str, ts: int, device_id: str) -> bytes:
    return f"odin-approval-sig|v1|{aid}|{decision}|{dg}|{nonce}|{int(ts)}|{device_id}".encode("utf-8")


def pair_message(device_id: str, pub_b64: str) -> bytes:
    return f"odin-phone-pair|v1|{device_id}|{pub_b64}".encode("utf-8")


def fingerprint(pub_raw: bytes) -> str:
    k = hashlib.sha256(pub_raw).hexdigest()[:16]
    return "-".join(k[i:i + 4] for i in range(0, 16, 4))


def _load(p: pathlib.Path) -> dict:
    try:
        return json.loads(p.read_text()) if p.exists() else {}
    except Exception:
        return {}


def _save(p: pathlib.Path, d: dict) -> None:
    key_relay._atomic_write(p, json.dumps(d, indent=1))


def _pub(b64: str) -> Ed25519PublicKey:
    raw = base64.b64decode(str(b64).encode(), validate=True)
    if len(raw) != 32:
        raise PhoneApprovalError("bad phone public key")
    return Ed25519PublicKey.from_public_bytes(raw)


# ---------------------------------------------------------------- pairing (phone -> Anchor -> Mac; owner trusts on desktop)
def request_pairing(device_id: str, name: str, pub_b64: str, proof_b64: str) -> dict:
    """Phone asks to be paired. Stored as PENDING; nothing is trusted until the owner confirms on the desktop."""
    device_id = str(device_id or "").strip()[:64]
    if not device_id or not all(c.isalnum() or c in "-_" for c in device_id):
        raise PhoneApprovalError("bad device id")
    pk = _pub(pub_b64)
    try:   # proof of possession: the phone holds the private key of the key it registers
        pk.verify(base64.b64decode(str(proof_b64).encode(), validate=True), pair_message(device_id, pub_b64))
    except (InvalidSignature, ValueError):
        raise PhoneApprovalError("pairing proof does not verify")
    raw = base64.b64decode(pub_b64)
    with _LOCK:
        d = _load(DEVICES)
        cur = d.get(device_id)
        if cur and cur.get("pub") == pub_b64 and cur.get("status") in ("pending", "trusted"):
            return _public(device_id, cur)
        # a NEW key for a known device id never inherits trust: it is pending again (the owner re-confirms)
        d[device_id] = {"name": str(name or "phone")[:60], "pub": pub_b64, "fp": fingerprint(raw),
                        "status": "pending", "requested": int(time.time()),
                        "history": (cur or {}).get("history", []) + [{"ts": int(time.time()), "event": "pair-request"}]}
        _save(DEVICES, d)
        return _public(device_id, d[device_id])


def set_status(device_id: str, status: str, by: str = "owner", channel: str = "desktop") -> dict:
    """Owner action ON THE DESKTOP: trust or revoke a phone. Never reachable through the Anchor."""
    if status not in ("trusted", "revoked"):
        raise PhoneApprovalError("status must be trusted or revoked")
    with _LOCK:
        d = _load(DEVICES)
        if device_id not in d:
            raise PhoneApprovalError("unknown device")
        d[device_id]["status"] = status
        d[device_id].setdefault("history", []).append({"ts": int(time.time()), "event": status, "by": by, "channel": channel})
        _save(DEVICES, d)
        return _public(device_id, d[device_id])


def _public(device_id: str, rec: dict) -> dict:
    return {"device_id": device_id, "name": rec.get("name", ""), "fingerprint": rec.get("fp", ""),
            "status": rec.get("status", ""), "requested": rec.get("requested")}


def devices() -> list:
    return [_public(k, v) for k, v in sorted(_load(DEVICES).items())]


# ---------------------------------------------------------------- decisions
def phone_view(a: dict) -> dict:
    """What the phone needs to show and hash (the full approval content; never any secret value)."""
    keep = ("id", "pid", "kind", "title", "summary", "cwd", "files", "commands", "severity", "security",
            "member", "created", "status")
    return {k: a.get(k) for k in keep}


def _nonce_once(device_id: str, nonce: str) -> bool:
    with _LOCK:
        d = _load(NONCES); now = int(time.time())
        d = {k: v for k, v in d.items() if now - int(v) < NONCE_KEEP_S}
        tag = device_id + ":" + nonce
        if tag in d:
            return False
        d[tag] = now
        _save(NONCES, d)
        return True


def verify_decision(aid: str, envelope: dict, approval: dict | None, now: int | None = None) -> dict:
    """Open + verify a phone decision. Returns {"device_id", "decision", "note"} or raises PhoneApprovalError.
    Does NOT apply it — the caller applies through the SAME approve/reject path the desktop uses."""
    now = int(now if now is not None else time.time())
    if not approval:
        raise PhoneApprovalError("no such approval")
    if approval.get("status") != "pending":
        raise PhoneApprovalError("approval is not pending (already decided)")
    if approval.get("kind") in PHONE_KINDS_EXCLUDED:
        raise PhoneApprovalError("key requests are answered through the secure key field, not Approve")
    try:
        inner = json.loads(key_relay.open_envelope(envelope, aid, ENVELOPE_NAME))
    except key_relay.RelayError as e:
        raise PhoneApprovalError(f"envelope: {e}")
    except Exception:
        raise PhoneApprovalError("envelope content is not valid")
    device_id = str(inner.get("device_id", "")); decision = str(inner.get("decision", ""))
    dg = str(inner.get("digest", "")); nonce = str(inner.get("nonce", "")); note = str(inner.get("note", ""))[:200]
    try:
        ts = int(inner.get("ts", 0))
    except Exception:
        raise PhoneApprovalError("bad timestamp")
    if decision not in ("approve", "reject"):
        raise PhoneApprovalError("decision must be approve or reject")
    if not (16 <= len(nonce) <= 64):
        raise PhoneApprovalError("bad nonce")
    rec = _load(DEVICES).get(device_id)
    if not rec:
        raise PhoneApprovalError("unknown phone (pair it first)")
    if rec.get("status") != "trusted":
        raise PhoneApprovalError(f"phone is {rec.get('status', 'unknown')} — trust it on the desktop first")
    try:
        _pub(rec["pub"]).verify(base64.b64decode(str(inner.get("sig", "")).encode(), validate=True),
                                sig_message(aid, decision, dg, nonce, ts, device_id) + b"|" + note.encode("utf-8"))
    except (InvalidSignature, ValueError):
        raise PhoneApprovalError("signature does not verify (forged or altered)")
    if dg != digest(approval):
        raise PhoneApprovalError("the request changed since the phone showed it (digest mismatch) — reload and decide again")
    if ts > now + FUTURE_SKEW_S or now - ts > WINDOW_S:
        raise PhoneApprovalError("decision expired (older than 15 minutes) — decide again")
    if not _nonce_once(device_id, nonce):
        raise PhoneApprovalError("decision already used (replay)")
    return {"device_id": device_id, "decision": decision, "note": note}


# ---------------------------------------------------------------- reference phone side (used by tests; the app does the same in Dart)
def phone_sign_and_seal(sk, device_id: str, relay_pub_b64: str, approval_view: dict, decision: str,
                        nonce: str, ts: int, note: str = "") -> dict:
    dg = digest(approval_view)
    sig = sk.sign(sig_message(approval_view["id"], decision, dg, nonce, ts, device_id) + b"|" + note.encode("utf-8"))
    inner = {"device_id": device_id, "decision": decision, "digest": dg, "nonce": nonce, "ts": ts,
             "note": note, "sig": base64.b64encode(sig).decode()}
    return key_relay.seal(relay_pub_b64, json.dumps(inner), approval_view["id"], ENVELOPE_NAME)
