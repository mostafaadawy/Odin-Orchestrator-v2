#!/usr/bin/env python3
"""F-41 interim test (no LLM): a key request is desktop-only; no phone path can send a key. python f41i_test.py <root>"""
import sys, os, pathlib, re
root = pathlib.Path(sys.argv[1]).resolve(); os.chdir(root); sys.path.insert(0, str(root / "server"))
import projects, secret_store, api_v2
fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
R = {(r.path, list(r.methods)[0]): r.endpoint for r in api_v2.build_router().routes if hasattr(r, "endpoint")}
p = projects.create_project("F41 Shop", "shop", members=[{"name": "Email", "role": "Email"}], identifier="f41-shop")
r = secret_store.request_key(p["id"], "Email", "klaviyo", "KLAVIYO_KEY_F41", "test")
rows = R[("/approvals", "GET")](p["id"], 0)["approvals"]
kr = [x for x in rows if x.get("kind") == "key_request"]
check("1: the key request is listed", len(kr) == 1, rows)
check("2: ...marked desktop_only", bool(kr) and kr[0].get("desktop_only") is True, kr)
check("3: ...with 'Enter this key on the desktop'", bool(kr) and "Enter this key on the desktop" in kr[0].get("detail", ""))
other = [x for x in rows if x.get("kind") != "key_request"]
check("4: other approvals are not marked desktop_only", all(not x.get("desktop_only") for x in other))
dart = (root / "odin_app/lib/api/anchor_api.dart").read_text()
# step F (F-41 relay): the phone may call ONLY the sealed-envelope endpoint, never the plain-value one
check("5: the phone app has no call to the plain key endpoint", "/secrets/project-key'" not in dart and "/secrets/project-key\"" not in dart
      and ("/secrets" not in dart or "sendSealedKey" in dart))
poll = (root / "server/local_poller_http.py").read_text()
paths = set(re.findall(r'_brain_(?:post|delete)\(f?"([^"?{]+)', poll))
# PC-4 (owner 2026-10-12, D-1 -> PC-4): the poller may reach exactly TWO verified phone paths besides the F-41 relay:
# /approvals/<id>/decide-e2e (signed by a TRUSTED phone + sealed to the Mac; pc4_test) and /secrets/phone-pair (a pairing
# REQUEST only). Plain approve/reject and every other secret endpoint stay unreachable from the Anchor.
_appr = re.findall(r'_brain_(?:post|delete)\(f?"(/approvals[^"]*)"', poll)
check("6: the anchor poller cannot reach the plain key endpoint, plain approve/reject, or any other /secrets path",
      not any(x.startswith("/secrets") and x not in ("/secrets/project-key-e2e", "/secrets/phone-pair") for x in paths)
      and all(a.endswith("/decide-e2e") for a in _appr) and "/approve" not in poll and "/reject" not in poll, (paths, _appr))
ap = (root / "odin_app/lib/screens/approvals.dart").read_text()
if "class ApprovalActions" not in ap:
    check("7: the phone shows a desktop-only branch for key requests (no field, no Approve)", False, "no key-request branch: the phone offers Approve")
else:
    seg = ap[ap.index("class ApprovalActions"):]
    kseg = seg[seg.index("if (isKeyRequest(item))"):seg.index("return Row(")]
    # step F: the field (if any) lives in KeyRelayField, whose value goes only to onSend (sealed by the screen)
    krf = ap[ap.index("class KeyRelayField"):] if "class KeyRelayField" in ap else ""
    check("7: the phone shows a desktop-only branch for key requests (no plain field, no Approve)",
          "TextField" not in kseg and "onAct(aid, true)" not in kseg and (not krf or ("widget.onSend(" in krf and "http" not in krf)))
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
