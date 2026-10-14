#!/usr/bin/env python3
"""Run ONE remote command file on the VM through deploy_ssh (password never printed). usage: vm_exec.py <file> [--no-fw]"""
import sys, pathlib
V2 = pathlib.Path(__file__).resolve().parents[2]; sys.path.insert(0, str(V2 / "server"))
import deploy_ssh as d
if "--no-fw" not in sys.argv:
    fr = d.refresh_firewall(); print("firewall rule refresh:", "ok" if fr.get("ok", True) else "FAILED")
r = d.ssh_exec(pathlib.Path(sys.argv[1]).read_text(), timeout=900)
print(r.get("out") or "", r.get("err", "") or r.get("error", ""))
print("rc_ok:", r.get("ok"))
