"""
Read credentials from workspace/shared/oth/.cred — handling BOTH formats the owner uses:
  - `KEY=value`        (Klaviyo, Veeqo, …)
  - `key: value`       (azvmcred uses a colon + space)
Never printed/committed; workspace/shared/oth/.cred is gitignored.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
CRED = ROOT / "workspace" / "shared" / "oth" / ".cred"


def load() -> dict:
    out: dict[str, str] = {}
    try:
        for raw in CRED.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line and (":" not in line.split("=", 1)[0]):
                k, v = line.split("=", 1)
            elif ":" in line:
                k, v = line.split(":", 1)
            else:
                continue
            out[k.strip()] = v.strip()
    except Exception:
        pass
    return out


def get(key: str, default: str = "") -> str:
    return load().get(key, default)
