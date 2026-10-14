#!/bin/bash
# Build the PROMOTION PACKAGE: per-change patches against the REAL folder's files, verified with `git apply --check`
# on a TEMP copy of those real files. NEVER touches the real folder (read-only copy of the needed files only).
set -e
ISO=/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Consolidated; REAL=/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Orchestrator
OUT=$ISO/_research/promotion; rm -rf "$OUT"; mkdir -p "$OUT/patches"
cd $ISO
unmap(){ sed -e 's#odin_core_con#odin_core#g; s#odin_anchor_con#odin_anchor#g; s#AiAgentWorkSpace/Odin-Consolidated#AiAgentWorkSpace/Odin-Orchestrator#g; s#Odin-Consolidated/_external/VolatileWorkSpace#Desktop/VolatileWorkSpace#g'; }
mk(){ name=$1; shift; git diff --no-color pre-p2 -- "$@" | unmap > "$OUT/patches/$name.patch"; git ls-files --others --exclude-standard -- "$@" | while read f; do git diff --no-color --no-index /dev/null "$f" | unmap >> "$OUT/patches/$name.patch" || true; done; }
mk 01-p2a-agents-start-in-own-project-folder server/api_v2.py
git diff --no-color pre-p2 -- server/projects.py | unmap > "$OUT/patches/_projects_all.diff"
python3 - "$OUT/patches" <<'PY'
import sys, re, pathlib
d = pathlib.Path(sys.argv[1]); t = (d / "_projects_all.diff").read_text()
head, *hunks = re.split(r"(?m)^(?=@@ )", t)
ep = [h for h in hunks if "EasyPost" in h]; rest = [h for h in hunks if "EasyPost" not in h]
(d / "01-p2a-agents-start-in-own-project-folder.patch").open("a").write(head + "".join(rest) if rest else "")
(d / "05-fix-easypost-role-catalogue.patch").write_text(head + "".join(ep) if ep else "")
(d / "_projects_all.diff").unlink()
PY
mk 02-p2b-owner-scope-hook server/scope_hook.py server/door_cli.py server/claude_cli.py
mk 03-p2a-relative-repo-path-in-instructions workspace/shared/directions/PHASE7-HANDOFF.md workspace/docs/ODIN_PHASES_TECH_DOC.md workspace/docs/README_ANCHOR_AND_INTEGRATIONS.md workspace/docs/SETUP-AND-TEST.md
# the copy expanded "~/Desktop" to an absolute path; restore the real file's spelling in removed/context lines
python3 - "$OUT/patches/03-p2a-relative-repo-path-in-instructions.patch" "$REAL" <<'PY2'
import sys, re, pathlib
p = pathlib.Path(sys.argv[1]); real = pathlib.Path(sys.argv[2]); out = []; cur = None
for ln in p.read_text().splitlines(keepends=True):
    m = re.match(r"^--- a/(.*)$", ln.rstrip("\n"))
    if m: cur = (real / m.group(1)).read_text()
    if cur is not None and ln[:1] in "- " and not ln.startswith("---") and ln[1:].rstrip("\n") not in cur:
        alt = ln.replace("/Users/mostafaadawy/", "~/")
        if alt[1:].rstrip("\n") in cur: ln = alt
    out.append(ln)
p.write_text("".join(out))
PY2
mk 04-fix-delete-leaves-scope-rows server/workspace_mw.py
# 05 EasyPost catalogue entry lives in projects.py together with 01 — split it out by hunk
# verify every patch applies to a TEMP copy of the REAL files
V=$ISO/_research/tmp/promo_verify; rm -rf "$V"; mkdir -p "$V"; cd "$V"; git init -q
for f in server/projects.py server/api_v2.py server/claude_cli.py server/workspace_mw.py workspace/shared/directions/PHASE7-HANDOFF.md workspace/docs/ODIN_PHASES_TECH_DOC.md workspace/docs/README_ANCHOR_AND_INTEGRATIONS.md workspace/docs/SETUP-AND-TEST.md; do mkdir -p "$(dirname $f)"; cp "$REAL/$f" "$f"; done
git add -A >/dev/null; git -c user.name=v -c user.email=v@l commit -qm real
for p in "$OUT"/patches/*.patch; do if git apply --check "$p" 2>"$p.check"; then echo "APPLIES $(basename $p)"; rm -f "$p.check"; else echo "FAILS $(basename $p)"; cat "$p.check"; fi; done
for p in "$OUT"/patches/*.patch; do git apply "$p"; done; python3 -c "import ast,sys;[ast.parse(open(f).read()) for f in ('server/projects.py','server/api_v2.py','server/claude_cli.py','server/workspace_mw.py','server/scope_hook.py','server/door_cli.py')];print('patched real-copy compiles')"
git diff --stat HEAD; git status --porcelain | head
