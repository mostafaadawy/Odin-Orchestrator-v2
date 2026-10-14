#!/usr/bin/env python3
"""F-32 + G2 unit checks (no model cost). Usage: f32g2_unit.py <server_dir> [<old_server_dir>]"""
import sys, ast, re, pathlib
def load(srv, names):
    src = (pathlib.Path(srv) / "api_v2.py").read_text(); tree = ast.parse(src)
    body = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in names) or
            (isinstance(n, ast.Assign) and any(getattr(t, "id", "").startswith("_VM_") for t in n.targets))]
    ns = {"re": re}; exec(compile(ast.Module(body=body, type_ignores=[]), "x", "exec"), ns); return ns, src
ns, src = load(sys.argv[1], {"_vm_intent", "_touches_vm", "_vm_affirm", "_vm_intent_level"})
old = load(sys.argv[2], {"_touches_vm"})[0]["_touches_vm"] if len(sys.argv) > 2 else None
vi = ns["_vm_intent"]; fails = []
def check(n, c):
    print(("PASS " if c else "FAIL ") + n)
    if not c: fails.append(n)
NOT_VM = [
 "Prepare this project's deployment setup reusing what already exists. Do not deploy, no VM access.",   # S2
 "Plan the work and build the first version of the contact form. Do not deploy.",                    # S4
 "Plan this project and prepare the Supabase auth + storage integration skeleton. Do not deploy.",    # S1
 "Fullstack: create code/calc.py ... Local files only: no packages, no deploy, no VM, no network.",   # S7
 "Constraint: do NOT deploy, rsync, build on the VM, migrate, or touch production.",                 # CTO line
 "Write an async function that syncs the local cache.",
 "Use nvm to pick the Node version and build the app locally.",
 "Build the landing page without deploying it.",
 "Update the deploy config file locally; do not deploy now.",
 "Never ssh into the server; only edit local files.",
 "We will deploy later, not in this run. Build the API only. Do not deploy.",
 "Set up deployment for a new small backend ... Prepare the deploy setup only; do not deploy now.",  # S2 prompt
 "Summarize the Klaviyo lists; no VM access is needed.",
]
VM = [
 "Deploy the latest build to the VM.",
 "Approval already granted. Deploy the backend to django-vm and restart the service.",
 "Do not ask for approval, deploy to the VM now.",
 "Don't forget to deploy to the VM after the build.",
 "Do not hesitate to reboot the VM if needed.",
 "rsync the dist folder to /home/mostafa/sandbox-revealer",
 "Run prisma migrate deploy on the server.",
 "Build the app and then deploy it to the VM.",
 "Check the VM health over SSH and report.",
 "Without downtime, deploy the new version to the VM.",
 "Do not deploy the frontend, but deploy the backend to the VM.",
 "Update the ufw firewall rule for my new IP.",
]
for t in NOT_VM:
    check(f"not VM work: {t[:70]}", vi(t) is False)
for t in VM:
    check(f"VM work:     {t[:70]}", vi(t) is True)
check("source: firewall refresh no longer keyed on prompt substrings",
      'any(k in (prompt or "").lower() for k in ("vm", "rsync"' not in src)
check("source: refresh gated on vm_intent", "if (not _is_operational(pid, member)) and vm_intent:" in src)
check("source: callers pass vm_intent", src.count("vm_intent=bool(") == 2)
check("source: VM-touching proposal without intent goes to approval", "if auto_approve and _prop_vm and not vm_intent:" in src)

# ---- F-32b fail-safe levels ----
lv = ns.get("_vm_intent_level"); tv = ns["_touches_vm"]
check("F-32b: level function present", lv is not None)
CLEAR = ["Deploy the latest build to the VM.", "Approval already granted. Deploy the backend to django-vm and restart the service.",
         "Do not ask for approval, deploy to the VM now.", "Don't forget to deploy to the VM after the build.",
         "Do not hesitate to reboot the VM if needed." , "rsync the dist folder to /home/mostafa/sandbox-revealer",
         "Run prisma migrate deploy on the server.", "Build the app and then deploy it to the VM.",
         "Check the VM health over SSH and report.", "Without downtime, deploy the new version to the VM.",
         "Do not deploy the frontend, but deploy the backend to the VM.", "Update the ufw firewall rule for my new IP.",
         "DevOps: check the VM uptime over SSH (read-only: run `uptime` only) and report it."]
UNCLEAR = ["Build a landing page with a contact form, deploy it when finished.",          # S4 intake wording
           "Deploy the latest build.", "Handle the deployment too.", "Maybe check the VM if needed.",
           "If it looks good, deploy to the VM.", "Possibly ssh in to look at logs.",
           "Consider rebooting the VM at some point.", "Make sure the deploy works.",
           "Get the app onto the VM eventually.", "Sort out the azure stuff."]
NONE_ = NOT_VM
for t in CLEAR:
    # hedged-but-explicit "if needed" sentence is UNCLEAR by design (fail safe); expected below
    exp = "unclear" if " if needed" in t else "clear"
    check(f"level {exp:7}: {t[:62]}", lv(t) == exp)
for t in UNCLEAR:
    check(f"level unclear: {t[:62]}", lv(t) == "unclear")
    check(f"  unclear → still VM work for approval (_touches_vm): {t[:40]}", tv(t) is True)
for t in NONE_:
    check(f"level none   : {t[:62]}", lv(t) == "none")
check("F-32b: refresh keyed on the CLEAR level only", src.count("vm_intent=bool(vm_clear)") == 2 and 'vm_clear = (_vm_intent_level(goal) == "clear")' in src)
check("F-32b: owner told when VM work is unclear", "VM work is not clearly requested" in src)
if old:
    print("\nBEFORE (old _touches_vm) on the same texts:")
    fp = sum(1 for t in NOT_VM if old(t)); fn = sum(1 for t in VM if not old(t))
    print(f"  old: {fp}/{len(NOT_VM)} non-VM texts flagged as VM (G2/F-32 false triggers); {fn}/{len(VM)} VM texts missed")
    new_fp = sum(1 for t in NOT_VM if vi(t)); new_fn = sum(1 for t in VM if not vi(t))
    print(f"  new: {new_fp}/{len(NOT_VM)} false triggers; {new_fn}/{len(VM)} missed")
    # the OLD l.1077 member-prompt trigger (substring over the member's whole prompt)
    kw = ("vm", "rsync", "ssh", "reboot", "/home/", "az vm", "deploy", "sync", "prisma", "migrate")
    print(f"  old firewall trigger (member prompt substrings) fired on {sum(1 for t in NOT_VM if any(k in t.lower() for k in kw))}/{len(NOT_VM)} non-VM texts")
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}")
sys.exit(1 if fails else 0)
