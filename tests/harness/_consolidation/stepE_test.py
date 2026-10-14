"""Step E / F-14 test: no owner secret is compiled into the source; the desktop reads them from the Keychain.
usage: stepE_test.py <tree-root> <file-list> <iso-repo>
Never prints a secret value — only counts and file names."""
import os, re, sys, json, subprocess, tempfile, pathlib, stat
root, flist, iso = sys.argv[1], sys.argv[2], sys.argv[3]
files = [l for l in open(flist).read().split('\n') if l]
R = re.compile(r'od_anchor_[A-Za-z0-9_-]{20,}')
old = subprocess.run(['git', '--no-optional-locks', 'show', 'stepE-start:desktop/src/App.jsx'], cwd=iso,
                     capture_output=True, text=True).stdout
known = [m.group(2) for m in re.finditer(r'const (ANCHOR_KEY|MANAGE_PASSWORD) = "([^"]+)"', old)]
ok = 0; bad = 0
def check(name, cond, info=''):
    global ok, bad
    print(('PASS ' if cond else 'FAIL ') + name + (('  ' + info) if info else '')); ok += bool(cond); bad += (not cond)
check('0 reference secrets loaded from stepE-start (values hidden)', len(known) == 2, f'n={len(known)}')
hits_pat, hits_known = [], []
for f in files:
    p = os.path.join(root, f)
    if not os.path.isfile(p) or os.path.getsize(p) > 20_000_000: continue
    try: b = open(p, 'rb').read()
    except Exception: continue
    s = b.decode('utf-8', 'replace')
    if R.search(s): hits_pat.append(f)
    if any(k in s for k in known): hits_known.append(f)
check('1 no anchor-key literal (od_anchor_…) in any shipped/tracked file', not hits_pat, f'{len(hits_pat)} files: ' + ', '.join(hits_pat[:8]))
check('2 the old key/password values appear in no shipped/tracked file', not hits_known, f'{len(hits_known)} files: ' + ', '.join(hits_known[:8]))
app = open(os.path.join(root, 'desktop/src/App.jsx')).read()
check('3 App.jsx has no ANCHOR_KEY / MANAGE_PASSWORD constants and reads via ownerSecret()',
      'const ANCHOR_KEY' not in app and 'MANAGE_PASSWORD' not in app and 'ownerSecret("anchor-key")' in app)
pre = open(os.path.join(root, 'desktop/electron/preload.cjs')).read()
main = open(os.path.join(root, 'desktop/electron/main.cjs')).read()
check('4 preload exposes odin.secret and main registers secret-get', 'secret-get' in pre and 'ipcMain.handle("secret-get"' in main)
gen = ['anchor_prod.js', 'anchor_seed.js', 'workspace/anchor-layer/anchor_seed.js']
gi = subprocess.run(['git', 'check-ignore', '--no-index'] + gen, cwd=root if os.path.isdir(os.path.join(root, '.git')) else iso,
                    capture_output=True, text=True).stdout.split()
tracked = [g for g in gen if g in files]
check('5 generated key files are git-ignored and not shipped', set(gi) == set(gen) and not tracked, f'ignored={len(gi)} shipped={tracked}')
cfg = open(os.path.join(root, 'odin_app/lib/config.dart')).read()
check('6 Flutter config takes the key from --dart-define', cfg.count("String.fromEnvironment('ODIN_ANCHOR_KEY')") == 2)
# 7-11: the Keychain getter, against a STUB `security` (the real Keychain is never touched)
sec = os.path.join(root, 'desktop/electron/secrets.cjs')
if not os.path.isfile(sec):
    check('7 Keychain getter exists (desktop/electron/secrets.cjs)', False); print(f'RESULT {ok} pass {bad} fail'); sys.exit(1)
d = pathlib.Path(tempfile.mkdtemp()).resolve(); log = d / 'argv.log'
stub = d / 'security'
stub.write_text('#!/bin/bash\nprintf "%s\\n" "$*" >> "%s"\n' % ('%s', log) +
                'acct=""; while [ $# -gt 0 ]; do [ "$1" = "-a" ] && acct="$2"; shift; done\n'
                'case "$acct" in anchor-key) echo "STUBKEY-123";; manage-password) echo "STUBPW";; *) exit 44;; esac\n')
stub.chmod(0o755)
js = r'''
const { getSecret } = require(process.argv[1]); const bin = process.argv[2];
(async () => {
  const out = {};
  out.key = await getSecret("anchor-key", { securityBin: bin, env: {} });
  out.pw = await getSecret("manage-password", { securityBin: bin, env: {} });
  out.emailEnv = await getSecret("manage-email", { securityBin: bin, env: { ODIN_MANAGE_EMAIL: "dummy@example.test" } });
  out.emailNone = await getSecret("manage-email", { securityBin: bin, env: {} });
  out.bad = await getSecret("x; touch /tmp/pwn", { securityBin: bin, env: {} });
  out.bad2 = await getSecret("__proto__", { securityBin: bin, env: {} });
  console.log(JSON.stringify(out));
})();'''
r = subprocess.run(['node', '-e', js, sec, str(stub)], capture_output=True, text=True, timeout=60)
try: out = json.loads(r.stdout.strip().splitlines()[-1])
except Exception: out = {}; print('node stderr:', r.stderr[-400:])
calls = log.read_text().splitlines() if log.exists() else []
check('7 getter returns the Keychain value (stub) for anchor-key / manage-password', out.get('key') == 'STUBKEY-123' and out.get('pw') == 'STUBPW')
check('8 exact argv: find-generic-password -s odin-anchor -a <name> -w', bool(calls) and calls[0] == 'find-generic-password -s odin-anchor -a anchor-key -w', calls[0] if calls else '')
check('9 env fallback when the Keychain has no entry; null when neither', out.get('emailEnv') == 'dummy@example.test' and out.get('emailNone') is None)
check('10 names outside the allow-list are refused without calling security', out.get('bad') is None and out.get('bad2') is None and len(calls) == 4, f'calls={len(calls)}')
check('11 no injection side effect', not os.path.exists('/tmp/pwn'))
print(f'RESULT {ok} pass {bad} fail'); sys.exit(1 if bad else 0)
