#!/usr/bin/env python3
"""G7: the audit also scans tests/ for duplicates (with the G5 delta rules, incl. thin pointers to shared logic)."""
import pathlib, sys
R = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
def sub(path, old, new, count=1):
    p = R / path; s = p.read_text()
    assert s.count(old) == count, (path, old[:70], s.count(old)); p.write_text(s.replace(old, new))
AU = "server/workspace_audit.py"
sub(AU, '''        for sub in ("code", "deploy"):
            for p in WS.glob(f"projects/*/{sub}/**/*"):''', '''        for sub in ("code", "deploy", "tests"):      # G7: tests/ copies are capabilities too
            for p in WS.glob(f"projects/*/{sub}/**/*"):''')
sub(AU, '''        for sub in ("code", "deploy"):
            for f in proj.glob(f"{sub}/**/*"):''', '''        for sub in ("code", "deploy", "tests"):
            for f in proj.glob(f"{sub}/**/*"):''')
sub(AU, '''                m = re.search(r"delta over shared capability:\\s*(shared/[\\w./-]+)", head)
                if m and (WS / m.group(1)).is_file():
                    ex[rel] = f"declared delta over {m.group(1)}"''', '''                m = re.search(r"(?:delta over shared capability:|thin pointer to the shared[^\\n(]*\\()\\s*(?:workspace/)?(shared/[\\w./-]+)",
                              head, re.I)
                if m and (WS / m.group(1)).is_file():   # G7: also a declared thin pointer to shared logic
                    ex[rel] = f"declared delta / pointer over {m.group(1)}"''')
print("G7 applied")

# ---- G7 part 2: files inside a registered overlay FOLDER skip only the same-name check, not the identical-copy check (applied in-tree)
