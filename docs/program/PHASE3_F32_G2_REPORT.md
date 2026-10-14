# Phase 3, F-32 + G2 (VM keyword false triggers): before and after report

**Applied in:** Odin-Consolidated only. **v1 is untouched.**
- **Git:** tag `f32g2-start` (f902e74) → fix `b2e4b0d` → harness commits → tag **`f32g2-done` (f63ea15)**. CHANGELOG entry added.
- **Code:** `server/api_v2.py` only.
- **Model cost:** $3.42 (3 live runs). **Total $40.34 of the $100 Phase 3 cap.**
- **Paper v1 fingerprint:** unchanged.

## What was wrong

- **F-32:** in a pre-authorized run, the Azure firewall refresh (NSG update plus ufw rotation) fired when any of `vm, sync, deploy, ssh, rsync, …` appeared **anywhere in the member's prompt** as part of a word. That included:
  - "no VM";
  - "do not deploy";
  - "async";
  - the CTO's own line "Constraint: do NOT deploy, rsync, build on the VM".
- **G2:** "Do not deploy" was treated as VM work. This blocked pre-authorized local work and showed "This touches Azure/the VM".

## The fix

1. **New intent check, `_vm_intent()`:**
   - only whole words count;
   - it understands negation: "do not deploy", "no VM access", "without deploying", "deploy later", and negated lists all count as **not** VM work;
   - "don't forget to deploy" and "do not ask for approval, deploy to the VM" **still count as VM work**.
   - `_touches_vm()` now uses it. This fixes G2.
2. **The firewall refresh fires only when the run's goal really asks for VM or deploy work** (or the project is in deploy mode). Words in the member's prompt no longer trigger it. This fixes F-32.
3. **Extra safety:** in a pre-authorized run that was not asked for VM work, any proposal touching the VM goes to your **approval popup** instead of running.

## Results

| Check | Before | After | Verdict |
|---|---|---|---|
| **F-32 reproduction (S7: pre-authorized, "no deploy, no VM")** | S7 r1 and r2: **firewall refresh attempted, about 16 blocked Azure calls per run**, including the ufw rotation script | **S7 r3: 0 Azure calls**, still PASSED (files verified, QA ran) | ✅ |
| **G2 ("Do not deploy")** | "This touches Azure/the VM" lock in **8 of 8** earlier runs (S4 r1–r6, S2 r7, S1 r4) | **S4 r7: no lock, 0 Azure calls** | ✅ |
| **Positive control (S9: pre-authorized, "check the VM uptime over SSH")** | — | **Refresh still fires when really asked.** All 20 calls blocked by the shims; nothing reached Azure. | ✅ |
| Unit checks: 13 non-VM texts and 12 real VM texts (no cost) | Old rule: **13/13 false triggers**, and 1/12 real VM asks missed | **0/13 false triggers, 0/12 missed** | ✅ |
| Regression suite | 32/32 | **32/32** | ✅ |
| Your end-to-end tests | ALL GREEN 1/1 | **ALL GREEN 3/3 each** | ✅ |
| Fix #2 checks | — | still ALL PASS | ✅ |

## Flagged for you

1. **When VM work IS asked, the refresh still runs your full rotate function, including the ufw rotation.** That is the dry-run defect P8-2, which is step 3.11 in the order of work. F-32 only stops the false triggers.
2. **In S9, the DevOps member ran `ssh` and `az vm run-command` itself.** These are the write-enabled tools of a pre-authorized run, and all were blocked here. In v1 a pre-authorized VM task can do this, which is by design.
3. **Remaining risk:** the intent check is rule-based. An unusual wording could still be misread:
   - **If it misses a real VM request:** the run simply gets no firewall access, and VM proposals go to your approval. This is safe.
   - **If it reads VM work where there is none:** the old behaviour returns for that run.
4. **S4 r7 still ended NOT_DONE:** DevOps got the build step and wrote nothing. That is G11, not G2.
5. **v1 is unchanged.** Until the cutover, the advice stands: no pre-authorized runs in v1. `full-services-19jul` and `revealer-6978` have auto-approve ON.

**Next, after your approval:** fix #3 (approval bypass).

---

## Addendum: fail-safe change (your approval condition), F-32b and F-32c

**Rule now in force:** only a **clear, explicit** VM request opens VM access in a pre-authorized run. Unclear or "possible" wording gets **no** automatic VM access. You are told, and any VM step goes to your approval.

| Change | What it does |
|---|---|
| **F-32b** (`1193205`) | Three levels: **clear / unclear / none**. "Clear" means an action word aimed at a VM target, not negated and not hedged. Only "clear" opens the firewall refresh. "Unclear" still counts as VM work for approvals. Deploy-mode projects also need a clear goal. |
| **F-32c** (`a8ff6fb`), found by the live test | In the unclear test (S10 r1) there was no refresh, but **the agent ran `az vm run-command` itself**. A new engine guard (`novm_hook.py`) now blocks every VM or Azure command (ssh, scp, sftp, remote rsync, az, the VM address, Odin's VM helpers) whenever the run is not clearly about the VM. It covers read-only and write-enabled runs, and stays on even if the scope hook is off. |

| Test | Result |
|---|---|
| Unit: 13 clear, 10 unclear and 13 "none" wordings, including hedged ones ("maybe … if needed", "deploy when finished") | ALL PASS |
| Unit: the guard blocks 8 VM command forms and allows 6 local ones | ALL PASS |
| **Live S10 r1** (pre-authorized, "maybe check the VM uptime if needed"), before F-32c | No refresh, and you were told. **But the agent tried `az` itself** (shim blocked it). |
| **Live S10 r2**, after F-32c | **0 Azure calls reached the shims.** The guard blocked the agent's own `az vm run-command` before it ran. Run PASSED (local note written). |
| **Live S9 r2** (clear: "check the VM uptime over SSH") | The refresh still fires when clearly asked; all calls blocked by the shims. |
| Regression and your end-to-end tests | 32/32; ALL GREEN 3/3 |
