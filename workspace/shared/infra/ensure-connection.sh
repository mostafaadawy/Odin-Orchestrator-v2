#!/usr/bin/env bash
# ensure-connection.sh — SAFE, idempotent connection restore + health check.
#
# It ONLY ever OPENS the ports the public sites need and REPORTS status. It NEVER denies, flushes,
# resets, disables, or restarts anything — so running it can NOT break functionality or security.
# Run it on the VM any time a site seems unreachable; it brings the web ports back and tells you the
# real state. (SSH/port-22 single-IP tightening is a separate, deliberate action — not done here, so
# this can never lock you out.)
set -uo pipefail

echo "=== 1. ensure PUBLIC WEB PORTS are open (idempotent; only adds) ==="
sudo ufw allow 80/tcp  || true
sudo ufw allow 443/tcp || true

echo; echo "=== 2. ufw status ==="
sudo ufw status verbose 2>&1 | sed -n '1,20p'

echo; echo "=== 3. web/app services (report only — nothing restarted) ==="
systemctl list-units --type=service --state=running 2>/dev/null \
  | grep -iE 'nginx|node|organ|bend|odin|omh|redfend|travel' || echo "  (none matched)"

echo; echo "=== 4. nginx config sanity ==="
sudo nginx -t 2>&1 | tail -2

echo; echo "=== 5. local reachability (app health, independent of firewall) ==="
for p in 80 443 4013; do
  echo -n "  127.0.0.1:$p -> "
  curl -sS -m 5 -o /dev/null -w '%{http_code}\n' http://127.0.0.1:$p 2>&1 || echo "no response"
done

echo; echo "=== DONE — web ports ensured open. Nothing was denied, disabled, flushed, or restarted. ==="
echo "If a site still fails from the internet but 127.0.0.1 works here, check the Azure NSG (from your Mac: az network nsg rule list)."
