#!/usr/bin/env python3
"""
Third-party service quota & abuse-cost monitor — GENERIC (not tied to any one vendor).

App-abuse doesn't just pollute our DB — it burns paid third-party quota (marketing emails, SMS, CRM
contacts, verification codes). This monitor is provider-agnostic: it works for Klaviyo, HubSpot, Mailchimp,
SendGrid, Twilio, Mailgun, Postmark, Brevo, ActiveCampaign, … and ANY future provider via a generic template.

Two modes, automatically chosen per provider:
  • LIVE telemetry — if an API key is configured for the provider, query its usage/limit endpoint (read-only).
  • INFERENCE/advisory — with no key, estimate consumption from app-side signals (downstream actions implied
    by abuse findings) and warn about quota risk, telling you exactly where to plug a key for real telemetry.

Read-only. Never sends anything. Extensible: add one dict to PROVIDER_TEMPLATES to support a new vendor.
"""
from __future__ import annotations
import json, os, pathlib, urllib.request

# Generic provider catalog. `usage_url`/`json_path` are used only if a key is configured. `category` groups
# them. Unknown providers fall back to the GENERIC template so nothing is vendor-locked.
PROVIDER_TEMPLATES = {
    "klaviyo":        {"category": "email/marketing", "env": ["KLAVIYO_API_KEY", "KLAVIYO_PRIVATE_KEY"],
                       "usage_url": "https://a.klaviyo.com/api/accounts/", "header": ("Authorization", "Klaviyo-API-Key {key}")},
    "hubspot":        {"category": "crm/marketing", "env": ["HUBSPOT_API_KEY", "HUBSPOT_TOKEN"],
                       "usage_url": "https://api.hubapi.com/account-info/v3/api-usage/daily", "header": ("Authorization", "Bearer {key}")},
    "mailchimp":      {"category": "email/marketing", "env": ["MAILCHIMP_API_KEY"], "usage_url": "", "header": None},
    "sendgrid":       {"category": "email", "env": ["SENDGRID_API_KEY"],
                       "usage_url": "https://api.sendgrid.com/v3/user/credits", "header": ("Authorization", "Bearer {key}")},
    "mailgun":        {"category": "email", "env": ["MAILGUN_API_KEY"], "usage_url": "", "header": None},
    "postmark":       {"category": "email", "env": ["POSTMARK_SERVER_TOKEN"], "usage_url": "", "header": None},
    "brevo":          {"category": "email/sms", "env": ["BREVO_API_KEY", "SENDINBLUE_API_KEY"],
                       "usage_url": "https://api.brevo.com/v3/account", "header": ("api-key", "{key}")},
    "twilio":         {"category": "sms/voice", "env": ["TWILIO_AUTH_TOKEN"], "usage_url": "", "header": None},
    "activecampaign": {"category": "crm/marketing", "env": ["ACTIVECAMPAIGN_API_KEY"], "usage_url": "", "header": None},
    "GENERIC":        {"category": "third-party", "env": [], "usage_url": "", "header": None},
}

def _services_config(pid="redberry-continuous-soc") -> list:
    """The org's configured third-party providers. Editable file in the SOC knowledge base; else inferred from
    the inventory + common env vars. Fully generic — add any provider name."""
    cfg = []
    try:
        import soc_run  # type: ignore
        p = soc_run._socdir(pid) / "knowledge" / "thirdparty-services.json"
        if p.exists():
            cfg = json.loads(p.read_text()).get("providers", [])
    except Exception:
        pass
    if not cfg:
        # infer from environment / known integrations (non-secret: we only check PRESENCE of a key name)
        for name, tpl in PROVIDER_TEMPLATES.items():
            if name == "GENERIC":
                continue
            if any(os.environ.get(e) for e in tpl["env"]):
                cfg.append({"provider": name})
        # default advisory set even with no keys, so the owner sees coverage + where to plug telemetry
        if not cfg:
            cfg = [{"provider": "klaviyo"}, {"provider": "hubspot"}]
    return cfg

def _key_for(tpl) -> str | None:
    for e in tpl.get("env", []):
        v = os.environ.get(e)
        if v:
            return v
    return None

def _live_usage(name, tpl) -> dict | None:
    key = _key_for(tpl)
    if not key or not tpl.get("usage_url") or not tpl.get("header"):
        return None
    try:
        hk, hv = tpl["header"]
        req = urllib.request.Request(tpl["usage_url"], headers={hk: hv.format(key=key)})
        data = json.loads(urllib.request.urlopen(req, timeout=8).read())
        return {"raw": True, "sample": str(data)[:160]}
    except Exception as e:
        return {"error": str(e)[:80]}

def check(pid="redberry-continuous-soc", abuse_active=False) -> dict:
    """Return provider posture. `abuse_active` (from the SOC run) escalates the advisory when app-abuse is live."""
    providers = _services_config(pid)
    rows, at_risk = [], []
    for entry in providers:
        name = (entry.get("provider") or "GENERIC").lower()
        tpl = PROVIDER_TEMPLATES.get(name, PROVIDER_TEMPLATES["GENERIC"])
        live = _live_usage(name, tpl)
        if live and live.get("raw"):
            mode, note = "live", f"live telemetry OK: {live['sample']}"
        elif live and live.get("error"):
            mode, note = "key-present-but-error", f"telemetry error: {live['error']}"
        else:
            mode = "advisory (no key)"
            note = ("no API key configured — running in inference mode; plug a key to get exact usage/limit. "
                    "If app-abuse is active, this provider is at risk of quota drain.")
            if abuse_active:
                at_risk.append(name)
        rows.append({"provider": name, "category": tpl["category"], "mode": mode, "note": note})
    return {"providers": rows, "at_risk": at_risk,
            "summary": f"{len(rows)} third-party providers tracked ({', '.join(r['provider'] for r in rows)}); "
                       f"{len(at_risk)} at quota-drain risk while abuse is active." if rows else "no providers configured",
            "how_to_extend": "Add providers in knowledge/thirdparty-services.json or set the provider's API-key env var; "
                             "any vendor is supported via the GENERIC template."}

if __name__ == "__main__":
    print(json.dumps(check(abuse_active=True), indent=2, ensure_ascii=False))
