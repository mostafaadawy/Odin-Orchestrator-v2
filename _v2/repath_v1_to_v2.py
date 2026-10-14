"""P5-1b: point v2 at ITSELF. Every runtime reference to v1's folder (absolute paths in code, config, project data)
is redirected to Odin-Orchestrator-v2, so v2 never reads or writes v1. Records (chats, history, logs) and backup
files (*.bak*) keep their original text: they describe the past. Product/display names ("Odin-Orchestrator") are kept.
Writes _v2/repath_v1_to_v2_changed.json. usage: python3 _v2/repath_v1_to_v2.py [--dry]"""
import os, re, sys, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
DRY = "--dry" in sys.argv
SKIP_DIRS = {".git", "node_modules", "__pycache__"}
RECORDS = ("workspace/chats/", "workspace/history/", "workspace/logs/")
RULES = [
    (re.compile(r"AiAgentWorkSpace/Odin-Orchestrator(?!-v2)(?=[/\"'`\s,;:)\]}]|$)", re.M), "AiAgentWorkSpace/Odin-Orchestrator-v2"),
    (re.compile(r"(\"AiAgentWorkSpace\",\s*\")Odin-Orchestrator(\")"), r"\1Odin-Orchestrator-v2\2"),
    (re.compile(r"('AiAgentWorkSpace',\s*')Odin-Orchestrator(')"), r"\1Odin-Orchestrator-v2\2"),
    (re.compile(r"(pkill[^\n]*?)Odin-Orchestrator/desktop"), r"\1Odin-Orchestrator-v2/desktop"),
]
changed = {}
for dp, dns, fns in os.walk(ROOT):
    dns[:] = [d for d in dns if d not in SKIP_DIRS]
    rel_d = os.path.relpath(dp, ROOT).replace(os.sep, "/") + "/"
    for fn in fns:
        rel = (rel_d + fn).lstrip("./") if rel_d != "./" else fn
        if rel.startswith(RECORDS) or ".bak" in fn or rel.startswith("_v2/"):
            continue
        p = pathlib.Path(dp) / fn
        if p.is_symlink() or p.stat().st_size > 20_000_000:
            continue
        try:
            s = p.read_text()
        except Exception:
            continue                                   # binary
        n, t = 0, s
        for rx, rep in RULES:
            t, k = rx.subn(rep, t); n += k
        if n:
            changed[rel] = n
            if not DRY:
                p.write_text(t)
(ROOT / "_v2" / "repath_v1_to_v2_changed.json").write_text(json.dumps(changed, indent=1, sort_keys=True))
print(("DRY " if DRY else "") + f"{len(changed)} files, {sum(changed.values())} references")
