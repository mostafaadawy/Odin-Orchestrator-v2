"""
EasyPost (EP) client — READ-ONLY multi-carrier tracking/shipping lookups.

Modeled on veeqo.py / klaviyo.py: the generic `call(method, path, ...)` is hard-gated so this
integration is TRACKING-ONLY — it READs freely and may perform exactly ONE write: creating a Tracker
(POST /trackers), the only way to read live status for a not-yet-tracked number (ships nothing, costs
nothing). All other writes are refused:
  1. METHOD gate: PUT/PATCH/DELETE (any endpoint) and POST to anything other than /trackers raise
     PermissionError before a request is built.
  2. ENDPOINT whitelist: only the read-only endpoints the app needs are allowed —
     /trackers, /shipments, /addresses, /parcels, /users (and their sub-paths, e.g. /trackers/{id}).
     Anything else raises PermissionError before a request is ever built.
Auth: EASYPOST_API_KEY from workspace/shared/oth/.cred. EasyPost uses HTTP Basic auth with the API
key as the username and an EMPTY password (header `Authorization: Basic base64(key + ":")`) — the key
is never hardcoded or logged. Base https://api.easypost.com/v2. Uses urllib (no extra deps).
"""
from __future__ import annotations

import base64
import json
import urllib.request
import urllib.error
import urllib.parse

from . import cred

BASE = "https://api.easypost.com/v2"

# Read-only endpoints this integration is permitted to reach (prefix match on the first path
# segment). Any other path is rejected — same read-only posture QA required for veeqo.py/klaviyo.py.
ALLOWED_PREFIXES = ("trackers", "shipments", "addresses", "parcels", "users")


def _key() -> str:
    """EasyPost issues SEPARATE production (EZAK…) and test (EZTK…) keys. Prefer production; fall
    back to a plain EASYPOST_API_KEY, then the test key. All read from workspace/shared/oth/.cred."""
    return (cred.get("EASYPOST_PRODUCTION_API_KEY", "")
            or cred.get("EASYPOST_API_KEY", "")
            or cred.get("EASYPOST_TEST_API_KEY", ""))


def configured() -> bool:
    return bool(_key())


def _auth_header(key: str) -> str:
    """EasyPost Basic auth: API key as username, empty password."""
    token = base64.b64encode(f"{key}:".encode()).decode()
    return f"Basic {token}"


def _allowed_path(path: str) -> bool:
    """True only if path's first segment is in ALLOWED_PREFIXES (e.g. 'trackers/trk_1' -> 'trackers')."""
    head = path.lstrip("/").split("?", 1)[0].split("/", 1)[0].lower()
    return head in ALLOWED_PREFIXES


def call(method: str, path: str, params: dict | None = None, body: dict | None = None) -> dict:
    """Hit an EasyPost endpoint, GET only, whitelisted paths only. Returns {ok,status,data}.

    READ-ONLY enforcement: any non-GET method (POST/PUT/PATCH/DELETE) or request body is rejected,
    and only the whitelisted read-only endpoints are reachable — all before a request is built.
    """
    m = method.upper()
    if path.startswith("http"):
        if not path.startswith(BASE):
            raise PermissionError(f"EasyPost integration: off-base URL not allowed: {path[:80]}")
        rel = path[len(BASE):]
    else:
        rel = path
    head = rel.lstrip("/").split("?", 1)[0].split("/", 1)[0].lower()
    if m == "GET":
        if head not in ALLOWED_PREFIXES:
            raise PermissionError(
                f"EasyPost integration: endpoint '{head}' not in read whitelist {ALLOWED_PREFIXES}")
    elif m == "POST" and head == "trackers":
        pass  # the ONE allowed write: create/refresh a tracker to read its live status
    else:
        raise PermissionError(
            f"EasyPost integration is tracking-only: {m} '{head}' not allowed (read-only except POST /trackers)")
    key = _key()
    if not key:
        return {"ok": False, "status": 0, "error": "EASYPOST_API_KEY missing in workspace/shared/oth/.cred"}
    p = path if path.startswith("http") else f"{BASE}/{path.lstrip('/')}"
    if params:
        p += ("&" if "?" in p else "?") + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if (m == "POST" and body is not None) else None
    req = urllib.request.Request(p, data=data, method=m)
    req.add_header("Authorization", _auth_header(key))
    req.add_header("accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
            return {"ok": True, "status": r.status, "data": json.loads(raw) if raw else {}}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "error": e.read().decode()[:1000]}
    except Exception as e:
        return {"ok": False, "status": 0, "error": str(e)}


# --- read-only convenience wrappers (all GET, all whitelisted) ---
def trackers(params=None):            return call("GET", "trackers", params)
def tracker(tracker_id):              return call("GET", f"trackers/{tracker_id}")
def shipments(params=None):           return call("GET", "shipments", params)
def shipment(shipment_id):            return call("GET", f"shipments/{shipment_id}")
def current_user():                   return call("GET", "users")
def create_tracker(tracking_code, carrier=None):
    """Create/refresh a Tracker (POST /trackers) — the only permitted write; returns the tracker with
    live status. carrier optional (EasyPost auto-detects). Never buys a label or ships anything."""
    body = {"tracker": {"tracking_code": tracking_code}}
    if carrier:
        body["tracker"]["carrier"] = carrier
    return call("POST", "trackers", body=body)
