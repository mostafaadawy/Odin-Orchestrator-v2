# Runbook: Mobile / Phone Access

**Owner agent:** Backend · **Reviewer:** Security & Compliance
**Gate:** local LAN use is safe (no approval). **Internet exposure is APPROVAL-GATED** and ties
into the Azure secure-connection procedure.

The mobile UI is `dashboard/mobile.html` (phone-optimized voice + chat). It talks to the same
server endpoints (`/chat`, `/dispatch`, `/voice/*`) and routes through the Brain dispatcher.

---

## Option A — Same Wi-Fi (LAN), recommended for now  *(no approval)*
1. Set a token so the API isn't open on your network:
   ```bash
   export ODIN_ACCESS_TOKEN="$(openssl rand -hex 16)"   # copy this value
   ```
2. Bind the server to your LAN (instead of 127.0.0.1):
   ```bash
   USE_VOICE=1 PORT=8000 uvicorn server.app:app --host 0.0.0.0 --port 8000
   ```
3. Find your Mac's LAN IP (`ipconfig getifaddr en0`), then on your phone (same Wi-Fi) open:
   `http://<mac-lan-ip>:8000/mobile.html` and paste the token when prompted.

> Note: browser mic capture needs a secure context. `localhost` is secure; a plain
> `http://<lan-ip>` is **not**, so the mic may be blocked on the phone. Use Option B (TLS) for
> reliable mic, or type instead of speaking on LAN.

## Option B — Secure internet exposure  *(APPROVAL REQUIRED — ties to Azure procedure)*
Do NOT expose directly. Front it with the existing reverse proxy on the Azure VM, behind TLS,
the **IP allowlist**, and the access token. Raise an approval request (`approval-template.md`,
category `config-change` + `azure-vm-action`) covering:
- proxy route `/odin/` → the Odin server (kept on loopback/private only),
- valid TLS cert (per `ssl-certificate.md`),
- NSG/firewall unchanged except as explicitly approved (respect the dynamic-IP procedure),
- `ODIN_ACCESS_TOKEN` required; rate-limit the proxy.
Only after approval and Security sign-off does exposure go live. Provides a real HTTPS origin,
so the phone mic works.

## Security rules (always)
- Never expose the Odin server unauthenticated. `ODIN_ACCESS_TOKEN` gates `/chat`, `/dispatch`,
  `/voice/*` (dashboard + `/health` stay open so the page can load and prompt for the token).
- Never widen Azure exposure to enable mobile access without approval.
- The dispatcher still enforces the approval gate for risky actions, even over mobile.
