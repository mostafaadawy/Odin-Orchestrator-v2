#!/bin/bash
# ---------------------------------------------------------------------------------------------------------
# Odin SOC — tiny 24/7 evidence sensor for a SMALL, BUSY VM (e.g. 8GB running many sites).
#
# Design: capture only CHEAP, read-only signals into a compact rolling log. NO analysis here (no LLM, no
# heavy scans) — the desktop brain's agents analyze this log when online (catch-up). This keeps the VM safe.
# Hard resource caps are enforced by the systemd unit (CPUQuota=4%, MemoryMax=48M) + nice/ionice below.
#
# Output: one JSON line per run appended to /home/mostafa/soc-sensor/events.jsonl (auto-rotated at ~5MB).
# ---------------------------------------------------------------------------------------------------------
set -euo pipefail
OUT_DIR="/home/mostafa/soc-sensor"
LOG="$OUT_DIR/events.jsonl"
mkdir -p "$OUT_DIR"

# be maximally polite to the websites sharing this VM
renice -n 19 -p $$ >/dev/null 2>&1 || true
ionice -c3 -p $$ >/dev/null 2>&1 || true

ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
# cheap signals only (each is a single fast read):
load=$(cut -d' ' -f1 /proc/loadavg 2>/dev/null || echo 0)
memfree=$(awk '/MemAvailable/{print $2}' /proc/meminfo 2>/dev/null || echo 0)
diskpct=$(df -P / 2>/dev/null | awk 'END{gsub("%","",$5); print $5}')
# failed ssh logins in the last capture window (bounded to last 200 lines — no full log scan)
authfail=$(tail -n 200 /var/log/auth.log 2>/dev/null | grep -c "Failed password" || echo 0)
# count of externally-listening non-80/443/22 ports (defense-in-depth drift signal)
extports=$(ss -ltn 2>/dev/null | awk '{print $4}' | grep -E '0.0.0.0|::' | grep -vE ':80$|:443$|:22$' | wc -l | tr -d ' ')
# top process cpu (comm only; excludes this sensor + its tools)
topcpu=$(ps -eo pcpu,comm --sort=-pcpu 2>/dev/null | awk 'NR==2{print $2"@"$1}')
# highest-count source IP hitting auth/subscribe in the last 300 nginx lines (cheap abuse signal)
topip=$(tail -n 300 /var/log/nginx/access.log 2>/dev/null | grep -aE '"(POST|GET) /(login|api/register|email-subscribe)' | awk '{print $1}' | sort | uniq -c | sort -rn | awk 'NR==1{print $2"="$1}')

printf '{"ts":"%s","load":%s,"mem_avail_kb":%s,"disk_pct":%s,"ssh_fail":%s,"ext_ports":%s,"top_cpu":"%s","top_auth_ip":"%s"}\n' \
  "$ts" "${load:-0}" "${memfree:-0}" "${diskpct:-0}" "${authfail:-0}" "${extports:-0}" "${topcpu:-}" "${topip:-}" >> "$LOG"

# rotate if big (keep it tiny on a small VM)
sz=$(stat -c%s "$LOG" 2>/dev/null || echo 0)
if [ "$sz" -gt 5000000 ]; then mv "$LOG" "$LOG.1"; fi
