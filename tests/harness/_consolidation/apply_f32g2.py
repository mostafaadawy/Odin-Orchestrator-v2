#!/usr/bin/env python3
"""F-32 + G2 (owner decision 2026-10-11: fix first, together).
F-32: in a pre-authorized run the Azure firewall refresh (NSG + ufw rotation) fired whenever a VM-ish SUBSTRING
      ("vm", "sync", "deploy", ...) appeared ANYWHERE in the member's prompt — incl. "no VM", "do not deploy",
      "async", and the CTO's own "Constraint: do NOT deploy …" line.
G2:   _touches_vm(goal) treated "do not deploy" as VM work (blocked pre-authorized local file work).
Fix:  _vm_intent(text): word-boundary terms + negation-aware (incl. negated lists, exceptions like
      "don't forget/hesitate/ask"). _touches_vm() uses it. _run_gated(vm_intent=…) refreshes the firewall ONLY when
      the RUN's goal affirmatively asks for VM/deploy work (or deploy mode) — never from the member prompt text.
      Defence in depth: a pre-authorized proposal that touches the VM in a run WITHOUT VM intent is NOT applied
      inline; it goes to the owner's approval popup."""
import pathlib, sys
R = pathlib.Path(__file__).resolve().parent.parent
api = R / "server/api_v2.py"; a = api.read_text()
if "F-32 + G2" in a: sys.exit("already applied")
def rep(old, new, name, count=1):
    global a
    assert a.count(old) == count, f"anchor {name}: {a.count(old)}"
    a = a.replace(old, new)

# 1) intent detector + _touches_vm uses it
rep('''def _touches_vm(goal: str) -> bool:
    """Does this run touch Azure/the VM (anything beyond local)? If so, it must ALWAYS go through
    the approval popup — read-only analysis runs free, but every VM/Azure STATE change waits for the
    owner's approve/discard, regardless of any 'authorized' phrasing in the brief."""
    g = (goal or "").lower()
    return any(k in g for k in ("azure", " vm", "vm ", "django-vm", "rsync", "/home/", "deploy",
                                "sync", "reboot", "prisma migrate", "ssh ", "run-command", "/bendcore",
                                "/organics", "control plane"))''',
'''_VM_TERMS = re.compile(
    r"(?<![\\w/-])(?:azure|django-vm|vms?|rsync|ssh|scp|reboot\\w*|re-?deploy\\w*|deploy\\w*|run-command|"
    r"control plane|prisma migrate|ufw|nsg|firewall)(?![\\w-])|/home/|/bendcore|/organics", re.I)
_VM_NEG = re.compile(r"\\b(?:no|not|never|don'?t|dont|do not|does not|doesn'?t|avoid|skip|nor|without|"
                     r"except|excluding|instead of|rather than|no need to|must not|mustn'?t|shouldn'?t|should not|"
                     r"won'?t|will not|cannot|can'?t)\\b", re.I)
_VM_NEG_EXC = re.compile(r"^\\s*(?:\\w+\\s+){0,1}(?:forget|hesitate|ask|wait|stop|fail|miss|delay|"
                         r"just|only|matter|later than)\\b", re.I)


def _vm_intent(text: str) -> bool:
    """F-32 + G2 (2026-10-11): does this text AFFIRMATIVELY ask for VM/Azure/deploy work?
    Word-boundary terms only ("async", "sync", "nvm" no longer match). A term is NEGATED when a negator
    precedes it closely in the same clause ("do not deploy", "no VM access", "without deploying"), or when it
    continues a negated list ("do NOT deploy, rsync, build on the VM, migrate"). Negators that do not negate
    the work ("don't forget to deploy", "do not ask for approval, deploy …") are ignored. Any NON-negated
    mention → True. Under a stated prohibition, noun uses such as "deploy setup/config/script" are local prep."""
    t = (text or "")
    if not _VM_TERMS.search(t):
        return False
    clauses = re.split(r"[.;!?\\n]+|\\bbut\\b|\\b(?:and )?then\\b|\\bafter that\\b", t, flags=re.I)
    affirm, negated_any = [], False
    for cl in clauses:
        prev_neg_end = None   # end index of the last NEGATED mention in this clause
        for m in _VM_TERMS.finditer(cl):
            before = cl[:m.start()]
            neg = False
            for n in _VM_NEG.finditer(before):
                gap = before[n.end():]
                if _VM_NEG_EXC.match(gap):
                    continue            # "don't forget to …", "do not ask for approval, …"
                gw = re.findall(r"[\\w'/-]+", gap)
                lim = 1 if n.group(0).lower() == "without" else 3
                if len(gw) <= lim and not (n.group(0).lower() == "without" and gw and gw[0].lower() not in ("any", "a", "the")):
                    neg = True
            if not neg and prev_neg_end is not None:   # continuation of a negated list
                gw = re.findall(r"[\\w'/-]+", cl[prev_neg_end:m.start()])
                if len(gw) <= 3 and not re.search(r"\\b(?:and then|please|must|should|now)\\b", cl[prev_neg_end:m.start()], re.I):
                    neg = True
            if not neg and re.match(r"\\W*(?:[\\w'-]+\\W+){0,2}?(?:later\\b|not now|not in this run|is not needed|isn'?t needed|"
                                    r"not needed|is not required|not required|out of scope)", cl[m.end():], re.I):
                neg = True              # postfix: "deploy later", "VM access is not needed"
            if neg:
                negated_any = True; prev_neg_end = m.end()
            else:
                affirm.append((cl, m))
    if not affirm:
        return False
    if negated_any:   # under a stated prohibition, noun uses of the term are local preparation, not VM work
        noun = re.compile(r"\\s+(?:setup|set-up|config\\w*|script\\w*|plan\\w*|files?|steps?|settings|"
                          r"pipeline|docs?|documentation|checklist|template\\w*|readme)\\b", re.I)
        prep = re.compile(r"(?:set\\s*up|setup|prepare|configure|plan|document|draft|write)\\s+(?:[\\w'-]+\\s+){0,2}$", re.I)
        affirm = [(cl, m) for (cl, m) in affirm
                  if not noun.match(cl[m.end():]) and not prep.search(cl[:m.start()])]
    return bool(affirm)


def _touches_vm(goal: str) -> bool:
    """Does this run touch Azure/the VM (anything beyond local)? If so, it must ALWAYS go through
    the approval popup — read-only analysis runs free, but every VM/Azure STATE change waits for the
    owner's approve/discard, regardless of any 'authorized' phrasing in the brief.
    F-32 + G2: negation-aware intent ("do not deploy", "no VM access" are NOT VM work)."""
    return _vm_intent(goal)''', "touches_vm")

# 2) _run_gated: firewall refresh only from the run's VM intent
rep('''def _run_gated(pid, member, scope, cid, prompt, model, folder, task_label="proposed changes",
               auto_approve=False):''', '''def _run_gated(pid, member, scope, cid, prompt, model, folder, task_label="proposed changes",
               auto_approve=False, vm_intent=False):''', "sig")
rep('''        if (not _is_operational(pid, member)) and any(k in (prompt or "").lower() for k in ("vm", "rsync", "ssh", "reboot", "/home/", "az vm", "deploy", "sync", "prisma", "migrate")):''',
    '''        # F-32 (2026-10-11): refresh the firewall ONLY when the RUN affirmatively asks for VM/deploy work
        # (vm_intent from the owner's goal / deploy mode) — never from words in the member's prompt
        # ("no VM", "do not deploy", "async", or the CTO's own constraint line used to trigger it).
        if (not _is_operational(pid, member)) and vm_intent:''', "trigger")

# 3) defence in depth: VM-touching proposal without VM intent → approval popup, never inline
rep('''    nf, nc = len(prop["files"]), len(prop["commands"])
    # NOT pre-authorized → create an approval and STOP.''',
    '''    nf, nc = len(prop["files"]), len(prop["commands"])
    # F-32: a pre-authorized run WITHOUT VM intent never applies VM-touching commands inline.
    _prop_vm = any(c.get("where") == "vm" for c in prop["commands"]) or \\
        any(k in str(c.get("cmd", "")) for c in prop["commands"] for k in ("rsync", "ssh ", "scp ", "@VM"))
    if auto_approve and _prop_vm and not vm_intent:
        auto_approve = False
        yield sse("status", {"icon": "🔒", "text": f"{member}: this proposal touches the VM, but this run was not asked to — it waits for your approval."})
    # NOT pre-authorized → create an approval and STOP.''', "guard")

# 4) callers pass the run's VM intent
rep('''                                       task_label=f"{fixer}: fix QA bug", auto_approve=auto_approve):''',
    '''                                       task_label=f"{fixer}: fix QA bug", auto_approve=auto_approve,
                                       vm_intent=bool(vm_work)):''', "call qa")
rep('''                                       task_label=f"{member}: {task[:50]} (try {_try})", auto_approve=auto_approve):''',
    '''                                       task_label=f"{member}: {task[:50]} (try {_try})", auto_approve=auto_approve,
                                       vm_intent=bool(vm_work or deploy_ctx)):''', "call member")
api.write_text(a); print("F-32 + G2 applied")
