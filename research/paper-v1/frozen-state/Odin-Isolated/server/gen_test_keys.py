#!/usr/bin/env python3
"""
gen_test_keys.py — ensure test auth keys exist + print them (the "test user" experience).

Guarantees workspace/shared/oth/.cred has ANCHOR_API_KEY and ODIN_API_KEY (generates strong random ones if
missing, never overwrites existing) and prints them so you can paste them into the app's
Settings and the third-party simulator. These enable the real auth path end-to-end.

Run:  python3 server/gen_test_keys.py
"""
from __future__ import annotations

import pathlib
import secrets

ROOT = pathlib.Path(__file__).resolve().parent.parent
CRED = ROOT / "workspace" / "shared" / "oth" / ".cred"


def _load() -> dict:
    out = {}
    if CRED.exists():
        for raw in CRED.read_text(encoding="utf-8").splitlines():
            s = raw.strip()
            if not s or s.startswith("#"):
                continue
            if "=" in s and (":" not in s.split("=", 1)[0]):
                k, v = s.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def ensure(name: str, existing: dict) -> tuple[str, bool]:
    if existing.get(name):
        return existing[name], False
    val = f"od_{name.split('_')[0].lower()}_{secrets.token_urlsafe(24)}"
    CRED.parent.mkdir(parents=True, exist_ok=True)
    with CRED.open("a", encoding="utf-8") as f:
        f.write(f"\n{name}={val}\n")
    return val, True


def main():
    existing = _load()
    anchor, a_new = ensure("ANCHOR_API_KEY", existing)
    odin, o_new = ensure("ODIN_API_KEY", existing)
    print("=" * 64)
    print("ODIN TEST KEYS  (test user — paste into the app Settings + the simulator)")
    print("=" * 64)
    print(f"  ANCHOR_API_KEY = {anchor}   {'(generated)' if a_new else '(existing)'}")
    print(f"  ODIN_API_KEY   = {odin}   {'(generated)' if o_new else '(existing)'}")
    print("-" * 64)
    print("  • App Settings → ANCHOR_API_KEY + ODIN_API_KEY fields (and token can stay blank).")
    print("  • Third-party simulator → X-API-Key field = ANCHOR_API_KEY.")
    print("  • Stored only in workspace/shared/oth/.cred (gitignored). Rotate anytime by deleting the lines.")
    print("=" * 64)


if __name__ == "__main__":
    main()
