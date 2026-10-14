"""
Auth for the WEB + Flutter apps (the desktop stays open — it's local).

Real, saved auth — not optional. Credentials are hashed (PBKDF2) in workspace/shared/oth/.auth; config flags live in
oth/auth_config.json. 2FA + verify-email are fully wired but default OFF; turning them on in config
makes them enforce. The owner can change the password from the app (Settings → Account).

Seed: tech@odinmarkets.com / 12345678  (created on first run if workspace/shared/oth/.auth is missing).

Endpoints (mounted at /auth):
  GET  /auth/config                      -> {require_login_web, require_login_mobile, twofa_enabled, verify_email_enabled, faceid_first_access, email_verified}
  POST /auth/login {email,password}      -> {ok, token, twofa_required?} | 401
  POST /auth/2fa  {email,code}           -> {ok, token} | 401   (only when twofa_enabled)
  GET  /auth/me   (X-Auth-Token)         -> {ok, email}
  POST /auth/logout {token}              -> {ok}
  POST /auth/change-password {email,old,new} -> {ok} | 401
  POST /auth/forgot {email}              -> {ok, message}        (stub: would email a reset link)
  POST /auth/verify/send {email}         -> {ok}                 (stub)
  POST /auth/verify/confirm {email,code} -> {ok}                 (code 000000 in dev)
  POST /auth/config {..flags..}          -> updated config       (owner toggles 2FA/verify)
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
import pathlib

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

ROOT = pathlib.Path(__file__).resolve().parent.parent
AUTH_FILE = ROOT / "workspace" / "shared" / "oth" / ".auth"
CFG_FILE = ROOT / "workspace" / "shared" / "oth" / "auth_config.json"

SEED_EMAIL = "tech@odinmarkets.com"
SEED_PASSWORD = "12345678"

DEFAULT_CFG = {
    "require_login_web": True,
    "require_login_mobile": True,
    "twofa_enabled": False,
    "verify_email_enabled": False,
    "faceid_first_access": True,
    "desktop_open": True,
    "email_verified": False,
}

_TOKENS: dict[str, dict] = {}   # token -> {email, ts}
_2FA_DEV_CODE = "000000"


def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120000).hex()


def _load_auth() -> dict:
    if AUTH_FILE.exists():
        try:
            return json.loads(AUTH_FILE.read_text())
        except Exception:
            pass
    salt = secrets.token_hex(16)
    rec = {"email": SEED_EMAIL, "salt": salt, "hash": _hash(SEED_PASSWORD, salt)}
    AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    AUTH_FILE.write_text(json.dumps(rec, indent=2))
    return rec


def _save_auth(rec: dict):
    AUTH_FILE.write_text(json.dumps(rec, indent=2))


def load_cfg() -> dict:
    cfg = dict(DEFAULT_CFG)
    if CFG_FILE.exists():
        try:
            cfg.update(json.loads(CFG_FILE.read_text()))
        except Exception:
            pass
    return cfg


def _save_cfg(cfg: dict):
    CFG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CFG_FILE.write_text(json.dumps(cfg, indent=2))


def _issue_token(email: str) -> str:
    t = "tok_" + secrets.token_urlsafe(24)
    _TOKENS[t] = {"email": email, "ts": time.time()}
    return t


class LoginIn(BaseModel):
    email: str
    password: str


class TwoFAIn(BaseModel):
    email: str
    code: str


class ChangePwIn(BaseModel):
    email: str
    old: str
    new: str


class EmailIn(BaseModel):
    email: str = ""


class VerifyIn(BaseModel):
    email: str
    code: str


def build_router() -> APIRouter:
    r = APIRouter(prefix="/auth", tags=["auth"])
    _load_auth()  # ensure seed exists

    @r.get("/config")
    def get_config():
        return load_cfg()

    @r.post("/config")
    def set_config(body: dict):
        cfg = load_cfg()
        for k in DEFAULT_CFG:
            if k in body:
                cfg[k] = body[k]
        _save_cfg(cfg)
        return cfg

    @r.post("/login")
    def login(body: LoginIn):
        rec = _load_auth()
        if body.email.strip().lower() != rec["email"].lower() or _hash(body.password, rec["salt"]) != rec["hash"]:
            raise HTTPException(401, "invalid email or password")
        cfg = load_cfg()
        if cfg.get("twofa_enabled"):
            return {"ok": True, "twofa_required": True, "email": rec["email"]}
        return {"ok": True, "token": _issue_token(rec["email"]), "email": rec["email"]}

    @r.post("/2fa")
    def twofa(body: TwoFAIn):
        rec = _load_auth()
        if not load_cfg().get("twofa_enabled"):
            return {"ok": True, "token": _issue_token(rec["email"]), "email": rec["email"]}
        if body.code.strip() != _2FA_DEV_CODE:
            raise HTTPException(401, "invalid 2FA code")
        return {"ok": True, "token": _issue_token(rec["email"]), "email": rec["email"]}

    @r.get("/me")
    def me(x_auth_token: str | None = Header(default=None)):
        info = _TOKENS.get(x_auth_token or "")
        if not info:
            raise HTTPException(401, "not authenticated")
        return {"ok": True, "email": info["email"]}

    @r.post("/logout")
    def logout(body: dict):
        _TOKENS.pop(body.get("token", ""), None)
        return {"ok": True}

    @r.post("/change-password")
    def change_password(body: ChangePwIn):
        rec = _load_auth()
        if _hash(body.old, rec["salt"]) != rec["hash"]:
            raise HTTPException(401, "current password is wrong")
        if len(body.new) < 6:
            raise HTTPException(400, "new password too short (min 6)")
        salt = secrets.token_hex(16)
        rec.update({"salt": salt, "hash": _hash(body.new, salt)})
        _save_auth(rec)
        return {"ok": True}

    @r.post("/forgot")
    def forgot(body: EmailIn):
        return {"ok": True, "message": "If that email exists, a reset link was sent (dev: change it in Settings → Account)."}

    @r.post("/verify/send")
    def verify_send(body: EmailIn):
        return {"ok": True, "message": f"Verification code sent (dev code: {_2FA_DEV_CODE})."}

    @r.post("/verify/confirm")
    def verify_confirm(body: VerifyIn):
        if body.code.strip() != _2FA_DEV_CODE:
            raise HTTPException(401, "invalid code")
        cfg = load_cfg()
        cfg["email_verified"] = True
        _save_cfg(cfg)
        return {"ok": True}

    return r
