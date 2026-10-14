# Runbook: Connect Odin from your Phone

The mobile page (`/mobile.html`) now uses the **persistent chats** (same memory + history as
desktop): chat menu (☰) to switch/new/delete, voice, EN/AR. To use it from your phone you need
(a) a way for the phone to reach the Mac, and (b) HTTPS (phones block the mic on plain http).

Always set a token first (so the API isn't open):
```
export ODIN_ACCESS_TOKEN="$(openssl rand -hex 16)"   # copy this; enter it on the phone
USE_VOICE=1 PORT=8000 uvicorn server.app:app --host 0.0.0.0 --port 8000
```

## Option A — Tailscale (recommended: private, secure, HTTPS, works anywhere)
Best for your security posture — a private encrypted mesh, no public exposure, no open ports,
no firewall changes.
1. Mac: `brew install --cask tailscale` → open it → sign in.
2. Phone: install the **Tailscale** app → sign in with the **same** account.
3. Mac: expose Odin over the tailnet **with HTTPS** (gives mic support):
   ```
   tailscale serve --bg https / http://localhost:8000
   tailscale serve status        # shows your https URL, e.g. https://mostafas-macbook-pro.tailXXXX.ts.net
   ```
4. Phone (Tailscale on): open that **https://…ts.net/mobile.html**, enter the token. Done — mic works.

## Option B — Cloudflare quick tunnel (fastest to try; public URL + token)
1. Mac: `brew install cloudflared`
2. `cloudflared tunnel --url http://localhost:8000`  → prints `https://<random>.trycloudflare.com`
3. Phone: open `https://<random>.trycloudflare.com/mobile.html`, enter the token.
   (Public URL, but protected by the token + the approval gate. URL changes each run.)

## Option C — same Wi‑Fi (LAN, quick, no mic)
1. `ipconfig getifaddr en0`  → your Mac's LAN IP.
2. Phone (same Wi‑Fi): `http://<mac-ip>:8000/mobile.html`, enter token.
   Typing works; the **mic won't** (plain http isn't a secure origin) — use A or B for voice.

## Security notes
- The token gates `/chat`, `/dispatch`, `/voice`, `/chats` (dashboard + `/health` stay open so the
  page can load and prompt for the token).
- Everything you do from the phone still runs through Odin's **approval gate**: read/inspect is
  free, any change to the VM/code needs your explicit yes.
- Tailscale keeps it private (recommended). Cloudflare is public-but-tokened; rotate/stop it when done.
