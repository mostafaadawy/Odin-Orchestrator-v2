# Anchor Phase 3 — settle the standalone Anchor on the VM

These artifacts dockerize `server/anchor_remote.py` (the `/anchor/v1` queue/auth/webhook service that in
Phase 2 ran locally on `:9100` as a stand‑in) and run it as a real, always‑on service on the VM with TLS.
**Nothing in the app code or the brain server changes** — this only packages and hosts the Anchor.

## Files here
- `Dockerfile` — tiny image (Python stdlib only); credentials are mounted, never baked in.
- `docker-compose.yml` — build + run, restart‑on‑crash, persisted queue volume.
- `odin-anchor.service` — systemd unit so it starts on boot and stays up.
- `nginx-anchor.conf` — HTTPS + reverse proxy (and optional serving of the web build).

## Deploy steps (on the VM)
1. Get the repo on the VM and put the real credentials at `oth/.cred` (gitignored — not in the image).
2. Build + run the container:
   ```
   cd infra/anchor
   docker compose up -d --build
   curl -s http://127.0.0.1:9100/health                # expect a healthy JSON response
   curl -s http://127.0.0.1:9100/anchor/v1/_status     # the queue/auth status
   ```
3. Keep it alive across reboots:
   ```
   sudo cp odin-anchor.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now odin-anchor
   ```
4. TLS + public URL:
   ```
   sudo cp nginx-anchor.conf /etc/nginx/sites-available/odin-anchor
   sudo ln -s /etc/nginx/sites-available/odin-anchor /etc/nginx/sites-enabled/
   # edit the file: replace anchor.YOURDOMAIN with the VM's domain
   sudo certbot --nginx -d anchor.YOURDOMAIN
   sudo nginx -t && sudo systemctl reload nginx
   ```
5. Point the Flutter app / pollers at `https://anchor.YOURDOMAIN/anchor/...` instead of `localhost:9100`.

## Notes
- The image carries only `server/`; it runs `python3 anchor_remote.py --host 0.0.0.0 --port 9100`.
- The queue persists in the `anchor-data` volume, so restarts don't lose pending tasks.
- This is **prepared, not executed** — run the steps above on the VM when you're ready.
