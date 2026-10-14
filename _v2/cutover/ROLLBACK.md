# Cutover rollback — back to v1 (written before step 2, owner condition C)

Rule: every step stops on its first failure and reports; nothing is pushed through. Roll back only what was done.
`B` = the folder in `_v2/cutover/LAST_BACKUP` (made by step 1). v1's own folder is never modified, so v1's code and files
need no restore.

## After step 2 (v1 stopped, records copied into v2)
Nothing in v1 changed. Start v1 again: open `/Applications/Odin.app` (still the v1 app at this point).

## After step 3 (database migrated)
```bash
export PATH=/opt/homebrew/opt/postgresql@14/bin:$PATH; B=$(cat ~/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2/_v2/cutover/LAST_BACKUP)
# quit both apps first; then restore the pre-cutover database exactly
pg_restore --clean --if-exists -d odin_core "$B/odin_core.dump"
pg_restore --clean --if-exists -d odin_anchor "$B/odin_anchor.dump"
# (the G8 step alone can also be undone with: bash server/migrations/migrate_g8.sh down odin_core)
```

## After step 4 (VM Anchor + web deployed, keys rotated)
```bash
cd ~/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2
# 1) old Odin folders on the VM (the guard's backup on the VM: /home/mostafa/odin_backups/<ts>/)
.venv/bin/python - <<'PY'
import sys; sys.path.insert(0, "server"); import deploy_ssh as d; d.refresh_firewall()
B = d.ssh_exec("ls -1d /home/mostafa/odin_backups/* | tail -1")["out"].strip()
print(d.ssh_exec(f"""set -e
tar -C /home/mostafa -xzf {B}/anchor-online.tgz
tar -C /home/mostafa -xzf {B}/odin-web.tgz
[ -f {B}/pg.conf ] && sudo cp -p {B}/pg.conf /etc/systemd/system/odin-anchor-online.service.d/pg.conf
sudo systemctl daemon-reload; sudo systemctl restart odin-anchor-online; sudo systemctl restart odin-web-online
echo restored {B}""")["out"])
PY
# 2) old secrets on the Mac (.cred backup written by the rotation, newest .cred.bak_rotate_*)
ls -t workspace/shared/oth/.cred.bak_rotate_* | head -1    # cp -p <that file> workspace/shared/oth/.cred
python3 server/odin_secrets.py keychain                     # Keychain back to the restored key
# 3) VM password: if it was rotated and must go back, Azure resets it (works without SSH):
#    az vm user update -g <rg> -n <vm> -u mostafa -p '<old password from the .cred backup>'
# 4) verify: python _v2/cutover/04a_vm_guard.py after   (RBO must still be identical)
```
The old v1 desktop build talks to the same Anchor URL, so v1 works again once the old Anchor folder and key are back.

## After step 6 (launchd job removed)
```bash
B=$(cat ~/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2/_v2/cutover/LAST_BACKUP)
cp -p "$B/com.odin.egypt-amazon-poster.plist" ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.odin.egypt-amazon-poster.plist
```

## After step 7 (new desktop app installed)
```bash
B=$(cat ~/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2/_v2/cutover/LAST_BACKUP)
osascript -e 'tell application "Odin" to quit'; mv /Applications/Odin.app ~/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2/_v2/cutover/Odin-v2.app
ditto "$B/Odin.app" /Applications/Odin.app
ditto "$B/app-support-odin-desktop" "$HOME/Library/Application Support/odin-desktop"
```
Then open Odin (v1). The phone app: reinstall the previous build from Xcode if needed (the phone keeps working against the
restored Anchor either way).
