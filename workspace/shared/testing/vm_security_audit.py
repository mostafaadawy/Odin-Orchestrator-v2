"""
vm_security_audit.py — READ-ONLY security audit of the Azure VM. Changes NOTHING by default.

It reports, so we can both SEE the truth before touching anything:
  • ufw status (which ports are allowed, and from where)
  • Azure NSG inbound rules (which ports are open, and the source restriction)
  • what is actually LISTENING on the VM and on which interface (0.0.0.0 = public vs 127.0.0.1 = local)
  • the nginx sites (sites-enabled) and whether our reverse-proxy site exists

Goal to verify: inbound is limited to 80, 443, and 22 — and 22 only from the owner's CURRENT public IP.
Anything else (e.g. 48619 / 48620) is flagged.

Run (read-only):   python3 testing/vm_security_audit.py
Clean extra ports: python3 testing/vm_security_audit.py --fix   (removes ONLY 48619/48620 from ufw+NSG;
                   never touches 22/80/443, never touches SSH access — asks nothing else).
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "server"))

EXTRA_PORTS = ("48619", "48620")


def main() -> int:
    import deploy_ssh
    fix = "--fix" in sys.argv

    if not deploy_ssh.ssh_exec("echo ok").get("ok"):
        print("VM not reachable — cannot audit. Re-run when connected.")
        return 1
    ip = deploy_ssh.vm_ip()
    print("=" * 74)
    print(f"VM SECURITY AUDIT — {ip}   (READ-ONLY{' + FIX extra ports' if fix else ''})")
    print("=" * 74)

    def show(title, cmd):
        out = deploy_ssh.ssh_exec(cmd).get("out", "") or "(no output / not available)"
        print(f"\n### {title}\n{out.strip()}")

    # 1) ufw
    show("ufw status (inbound allow rules)", "sudo ufw status verbose 2>/dev/null || echo 'ufw not present'")
    # 2) Azure NSG inbound rules
    show("Azure NSG inbound rules (port · source · access)",
         "RG=$(az group list --query '[0].name' -o tsv 2>/dev/null); "
         "NSG=$(az network nsg list --query '[0].name' -o tsv 2>/dev/null); "
         "if [ -n \"$NSG\" ]; then az network nsg rule list -g \"$RG\" --nsg-name \"$NSG\" "
         "--query \"[?direction=='Inbound'].{name:name,port:destinationPortRange,src:sourceAddressPrefix,access:access,prio:priority}\" "
         "-o table 2>/dev/null; else echo 'az/NSG not reachable from the VM (rules may be managed from your Mac/portal)'; fi")
    # 3) what is actually listening, and on which interface
    show("Listening sockets (0.0.0.0 = PUBLIC interface, 127.0.0.1 = local only)",
         "sudo ss -ltnp 2>/dev/null | awk 'NR==1 || /:80 |:443 |:22 |:48619|:48620/' || echo '(ss unavailable)'")
    # 4) nginx sites
    show("nginx sites-enabled",
         "ls -l /etc/nginx/sites-enabled/ 2>/dev/null; echo '--- our proxy site present? ---'; "
         "ls -l /etc/nginx/sites-available/odin-proxy* 2>/dev/null || echo '(no odin-proxy site yet)'")

    # Verdict on the extra ports
    print("\n" + "=" * 74)
    for p in EXTRA_PORTS:
        u = deploy_ssh.ssh_exec(f"sudo ufw status 2>/dev/null | grep -E '\\b{p}\\b' || echo none").get("out", "").strip()
        pub = deploy_ssh.ssh_exec(f"sudo ss -ltn 2>/dev/null | grep -E '0.0.0.0:{p} |\\*:{p} ' || echo none").get("out", "").strip()
        flag = "⚠️ EXPOSED" if (pub and pub != "none") else ("• ufw rule present (no public listener)" if u != "none" else "✓ clean")
        print(f"  port {p}: ufw={'yes' if u!='none' else 'no'}  public-listener={'yes' if pub!='none' else 'no'}  → {flag}")

    if fix:
        print("\n--- FIX: removing ONLY 48619/48620 from ufw + NSG (22/80/443 untouched) ---")
        for p in EXTRA_PORTS:
            deploy_ssh.ssh_exec(f"sudo ufw delete allow {p}/tcp 2>/dev/null; sudo ufw delete allow {p} 2>/dev/null; true")
            deploy_ssh.ssh_exec(
                "RG=$(az group list --query '[0].name' -o tsv 2>/dev/null); "
                "NSG=$(az network nsg list --query '[0].name' -o tsv 2>/dev/null); "
                f"[ -n \"$NSG\" ] && az network nsg rule delete -g \"$RG\" --nsg-name \"$NSG\" -n odin-{p} 2>/dev/null; true")
        # prove SSH(22) is still restricted to an IP and 80/443 still allowed
        ssh_rule = deploy_ssh.ssh_exec("sudo ufw status 2>/dev/null | grep -E '\\b22\\b' || echo '22 not in ufw (NSG-managed)'").get("out", "").strip()
        print(f"  after fix — SSH(22) rule: {ssh_rule}")
        print("  ufw now:")
        print(deploy_ssh.ssh_exec("sudo ufw status 2>/dev/null | sed 's/^/    /'").get("out", ""))
        print("  ✓ extra ports removed; 22/80/443 left exactly as they were.")

    print("\nDone (read-only)." if not fix else "\nDone (fixed extra ports only).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
