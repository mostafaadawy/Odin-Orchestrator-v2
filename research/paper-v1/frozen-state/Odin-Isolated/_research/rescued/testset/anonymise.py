"""Anonymise the raw extraction (keel/testset/_work/candidates.jsonl from extract.py).
Rules copied verbatim from the old build.py (ANON, SCOPE). No labels, no splits.
Usage: python3 anonymise.py candidates.jsonl raw_requests_anon.jsonl"""
import re, json, sys
ANON = [
 (r"\b\d{1,3}(?:\.\d{1,3}){3}\b", "<IP>"), (r"[\w.+-]+@[\w-]+\.[\w.]+", "<EMAIL>"),
 (r"\bMostafa\s+Adawy\b", "OWNER"), (r"/Users/[A-Za-z0-9_]+", "/Users/USER_A"), (r"/home/[A-Za-z0-9_]+", "/home/USER_A"),
 (r"\bmostafa\b", "USER_A"), (r"(?i)\bbendcore\b", "SERVICE_A"), (r"\bbend\|core\b", "svc"), (r"(?i)\borganics?(-frontend|-backend)?\b", r"PROJECT_A\1"),
 (r"(?i)\bRBO[-_ ]?Staging\b|\bRBO\b", "PROJECT_A"), (r"(?i)\bred\s?berry\b", "CLIENT_A"), (r"(?i)\brevealer\b", "PROJECT_B"),
 (r"(?i)\bodinmarkets\b", "COMPANY_A"), (r"(?i)\bodin\b", "SYSTEM"),
 (r"(?i)\b(klaviyo|clavio|clavu)\b", "EMAIL_PROVIDER"), (r"(?i)\b(veeqo|vq)\b", "FULFILMENT_PROVIDER"),
 (r"(?i)\bhubspot\b", "CRM_PROVIDER"), (r"(?i)\beasypost\b", "TRACKING_PROVIDER"),
 (r"nginx-backup-\d+\.tgz", "nginx-backup-<TS>.tgz"), (r"\b\d{7,}\b", "<NUM>"), (r"(?i)\bfuck\b", "[expletive]"),
]
def anon(s):
    for a, b in ANON: s = re.sub(a, b, s)
    return re.sub(r"\s+", " ", s).strip()
SCOPE = {"real-deployment-and-diagnosis-organics": "PROJECT_A_DEPLOY", "fulfillment-vq-status": "PROJECT_C_FULFILMENT_RO",
         "email-klaviyo": "PROJECT_D_EMAIL_RO", "hubspot-crm": "PROJECT_E_CRM", "redberry-continuous-soc": "PROJECT_F_SOC",
         "vm-sentinel": "PROJECT_G_VM_MONITOR", "shipping-veeqo": "PROJECT_C_FULFILMENT_RO"}
def scope_anon(s):
    for k, v in SCOPE.items():
        if k in s: return v
    return "GLOBAL_CHAT"
if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    with open(dst, "w") as fo:
        for l in open(src):
            r = json.loads(l)
            r["text"] = anon(r["text"]); r["scope"] = scope_anon(r.get("scope") or "")
            fo.write(json.dumps(r, ensure_ascii=False) + "\n")
