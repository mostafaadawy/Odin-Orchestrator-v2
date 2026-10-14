F=$(find /home/mostafa/workspace /home/mostafa/anchor-online -name anchor_manage.json 2>/dev/null | head -1)
[ -z "$F" ] && { echo "no anchor_manage.json found"; exit 1; }
B=/home/mostafa/odin_backups/manage_$(date +%Y%m%d_%H%M%S).json; cp -p "$F" "$B"; chmod 600 "$B"
python3 - "$F" <<'PY'
import json,sys; p=sys.argv[1]; d=json.load(open(p))
print("before: sessions", len(d.get("sessions",{})), "devices", len(d.get("devices",{})), "settings kept:", d.get("settings"))
d["sessions"]={}; d["devices"]={}; d["pending_codes"]={}
json.dump(d,open(p,"w"))
print("after: sessions 0, devices 0 (everyone signs in once more with the desktop code)")
PY
echo "file: $F  backup: $B"
