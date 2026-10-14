# =============================================================================
# deploy.config.sh — the ONLY file you edit to change a deploy.
# deploy.sh sources this if it exists. Anything you DON'T set keeps the
# built-in default, so an empty/clean config = the exact deploy that works today.
#
# Set a value to OVERRIDE a default. Leave it commented to keep the default.
# =============================================================================

# ---- folder mapping + per-target commands (override only what you need) ------
# CFG_BACKEND_LOCAL="/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Isolated/_external/VolatileWorkSpace/RBO-Staging/b"
# CFG_BACKEND_VM="/home/mostafa/RBO-Staging/b"
CFG_BACKEND_MIG="new"            # Additive migrations only (prisma migrate deploy). The 2026-07-16
                                 # destructive "reset" was a one-run authorization only; reverted per
                                 # the config's own note to remove the DB-wipe landmine for future runs.
# CFG_BACKEND_BUILD="rm -rf dist && npm run build"

# CFG_FRONTEND_LOCAL="/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Isolated/_external/VolatileWorkSpace/RBO-Staging/f"
# CFG_FRONTEND_VM="/home/mostafa/RBO-Staging/f"
# CFG_FRONTEND_MIG="none"
# CFG_FRONTEND_BUILD="rm -rf .next && npm run build"

# ---- excludes: ADD to / REMOVE from the safe defaults ------------------------
# Ignore MORE files/folders (added on top of the defaults):
# public/ + package.json are DEPLOYED now (site assets like captcha icons/photos + manifest). Keep only
# media blobs, the lockfile, and production uploads out of the sync.
CFG_EXTRA_EXCLUDES=( "*.mp4" "*.mp5" "*.copy" "package-lock.json" "uploads" )
# Stop ignoring something (e.g. to deploy NEW prisma migrations, drop it here):
CFG_DROP_EXCLUDES=( )
#   example: CFG_DROP_EXCLUDES=( "prisma/migrations" )

# ---- restart AFTER deploy (the "reboot solution") ----------------------------
# Restart ONLY these app services after the build. This re-runs bendcore's boot self-seed (which
# repopulates users/roles/captcha config after a DB reset) and loads the new frontend build — WITHOUT
# a full VM reboot that would drop the other 5 production sites on this shared box. Never touches
# nginx, ports, or the other sites.
CFG_RESTART_SERVICES=( "bendcore-staging" "organics-staging" )
CFG_REBOOT=0                   # do NOT full-reboot the shared VM (never damage the other sites).

# ---- EXTRA steps: services, a new subdomain folder, nginx proxy, etc. --------
# Each entry is ONE shell command run ON THE VM as mostafa, in order, AFTER the
# builds. This is where DevOps work that isn't a plain sync/build goes.
EXTRA_STEPS=( )
#
# Example — create a subdomain folder + an nginx reverse-proxy linking it to the
# main domain, then reload nginx (uncomment + adjust names/ports):
# EXTRA_STEPS=(
#   "mkdir -p /home/mostafa/shop"
#   "sudo tee /etc/nginx/sites-available/shop.organics.conf >/dev/null <<'NG'
# server {
#     server_name shop.organics.example.com;
#     location / { proxy_pass http://127.0.0.1:4020; proxy_set_header Host \$host; }
# }
# NG"
#   "sudo ln -sf /etc/nginx/sites-available/shop.organics.conf /etc/nginx/sites-enabled/"
#   "sudo nginx -t && sudo systemctl reload nginx"
# )
