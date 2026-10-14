#!/usr/bin/env python3
"""F-32b (owner, 2026-10-11): FAIL SAFE. Three levels from _vm_intent_level(): "clear" | "unclear" | "none".
- Only a CLEAR, explicit VM request (an action verb aimed at a VM target, not negated, not hedged) may trigger
  the firewall refresh / automatic VM access in a pre-authorized run.
- "unclear" (VM words with no explicit target, or hedged: "deploy when finished", "maybe check the VM if needed")
  gets NO refresh and NO automatic VM access; _touches_vm() treats it as VM work, so changes go to the owner's
  approval popup.
- "none" (no VM words, or only negated ones: "do not deploy", "no VM access") is local work (G2 stays fixed).
- Deploy-mode projects no longer auto-refresh on their own: the goal must be clear too."""
import pathlib, sys
R = pathlib.Path(__file__).resolve().parent.parent
api = R / "server/api_v2.py"; a = api.read_text()
if "F-32b" in a: sys.exit("already applied")
def rep(old, new, name):
    global a
    assert a.count(old) == 1, f"anchor {name}: {a.count(old)}"
    a = a.replace(old, new)
rep("def _vm_intent(text: str) -> bool:\n", "def _vm_affirm(text: str) -> list:\n", "rename")
rep('''    t = (text or "")
    if not _VM_TERMS.search(t):
        return False''', '''    t = (text or "")
    if not _VM_TERMS.search(t):
        return []''', "early")
rep('''    if not affirm:
        return False
    if negated_any:''', '''    if not affirm:
        return []
    if negated_any:''', "noaff")
rep('''                  if not noun.match(cl[m.end():]) and not prep.search(cl[:m.start()])]
    return bool(affirm)
''', '''                  if not noun.match(cl[m.end():]) and not prep.search(cl[:m.start()])]
    return affirm


def _vm_intent(text: str) -> bool:
    """Any NON-negated VM/deploy mention (clear or unclear). Used by _touches_vm(): VM work needs approval."""
    return bool(_vm_affirm(text))


_VM_ACT = re.compile(r"\\b(?:deploy\\w*|re-?deploy\\w*|ssh|rsync|scp|reboot|restart|check|run|connect|push|upload|"
                     r"migrate|update|open|apply|rotate|refresh|inspect|diagnose|read)\\b", re.I)
_VM_TGT = re.compile(r"(?<![\\w-])(?:vms?|django-vm|azure|server|production|prod|ufw|nsg|firewall)(?![\\w-])|/home/|/bendcore|/organics", re.I)
_VM_HEDGE = re.compile(r"\\b(?:if|maybe|perhaps|possibly|might|could|whether|optionally|when (?:ready|finished|done)|"
                       r"in case|eventually|at some point|consider|think about|should we)\\b", re.I)


def _vm_intent_level(text: str) -> str:
    """F-32b (fail safe): "clear" | "unclear" | "none". Only "clear" may open VM access automatically.
    CLEAR = an affirmative mention whose clause has an action verb aimed at a VM target within a few words, and
    no hedge ("if", "maybe", "when finished", ...). VM words without that are UNCLEAR."""
    affirm = _vm_affirm(text)
    if not affirm:
        return "none"
    for cl, m in affirm:
        if _VM_HEDGE.search(cl):
            continue
        for v in _VM_ACT.finditer(cl):
            tail = cl[v.start():]
            t = _VM_TGT.search(tail)
            if t and len(re.findall(r"[\\w'/.-]+", tail[:t.start()])) <= 6:
                return "clear"
    return "unclear"
''', "level")
# orchestrate: compute the CLEAR flag once; refresh/auto VM access only on it
rep("        vm_work = _touches_vm(goal) or deploy_mode\n",
    "        vm_work = _touches_vm(goal) or deploy_mode\n"
    "        vm_clear = (_vm_intent_level(goal) == \"clear\")   # F-32b: only an explicit VM request opens VM access\n"
    "        if vm_work and not vm_clear:\n"
    "            yield sse(\"status\", {\"icon\": \"🔒\", \"text\": \"VM work is not clearly requested in this goal — no automatic VM access; any VM step waits for your approval.\"})\n", "vmclear")
rep("vm_intent=bool(vm_work)):", "vm_intent=bool(vm_clear)):", "call qa")
rep("vm_intent=bool(vm_work or deploy_ctx)):", "vm_intent=bool(vm_clear)):", "call member")
api.write_text(a); print("F-32b applied")
