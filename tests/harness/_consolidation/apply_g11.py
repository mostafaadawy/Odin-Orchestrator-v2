#!/usr/bin/env python3
"""G11: a scoped request goes to DevOps only when it AFFIRMATIVELY asks for ops work (whole words, negation-aware);
"Do not deploy", "login", "catalog", "description", "feedback" no longer route a build to DevOps."""
import pathlib, sys
R = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
def sub(path, old, new, count=1):
    p = R / path; s = p.read_text()
    assert s.count(old) == count, (path, old[:70], s.count(old)); p.write_text(s.replace(old, new))
API = "server/api_v2.py"
sub(API, '''def _vm_affirm(text: str) -> list:''', '''def _vm_affirm(text: str, terms=None) -> list:''')
sub(API, '''    t = (text or "")
    if not _VM_TERMS.search(t):
        return []''', '''    t = (text or "")
    terms = terms or _VM_TERMS
    if not terms.search(t):
        return []''')
sub(API, '''        for m in _VM_TERMS.finditer(cl):
            before = cl[:m.start()]''', '''        for m in terms.finditer(cl):
            before = cl[:m.start()]''')
sub(API, '''    gl = (goal or "").lower()
    ops = any(k in gl for k in ("vm", "ssh", "deploy", "rsync", "server", "log", "journalctl",
                                "firewall", "nsg", "ufw", "trigger", "script", "psql", "db", "az "))''',
'''    # G11: whole words only and negation-aware ("Do not deploy" is NOT ops work; "login", "catalog",
    # "description", "feedback", "blog" no longer match "log"/"script"/"db"). Same rules as the VM check.
    ops = bool(_vm_affirm(goal or "", _OPS_TERMS))''')
sub(API, '''def _direct_member(pid: str, goal: str) -> str:''', '''_OPS_TERMS = re.compile(r"(?<![\\w-])(?:vms?|ssh|deploy\\w*|re-?deploy\\w*|rsync|servers?|logs?|journalctl|firewall|nsg|"
                        r"ufw|triggers?|scripts?|psql|db|az)(?![\\w-])", re.I)


def _direct_member(pid: str, goal: str) -> str:''')
print("G11 applied")
