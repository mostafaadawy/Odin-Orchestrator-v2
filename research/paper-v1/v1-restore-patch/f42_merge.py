"""F-42 merge (pure function, no I/O): bring back what the 2026-07-19 G10 rewrite removed from an agent's shared
capability.md, taking the 2026-07-18 version (v1 git 06a6ddb) as the source. MERGE ONLY:
  - every 'Integrated foundational charter' and '[archived] merged from duplicate agent' section that is missing
    is APPENDED whole (original order, original text);
  - every base custom rule that is missing is ADDED to the file's first '## Custom rules' section;
  - no existing line is changed or deleted (only a lone '- (none yet)' placeholder is dropped where a rule is added);
  - base title/description lines that differ are NOT touched (reported as 'left as is')."""
MARKERS = ("## Integrated foundational charter", "## [archived] merged from duplicate agent")
PLACEHOLDERS = ("- (none yet)", "- (none)")


def _blocks(text):
    lines = text.split("\n")
    idx = [i for i, l in enumerate(lines) if l.startswith(MARKERS)]
    base = lines[:idx[0]] if idx else lines
    out = []
    for n, i in enumerate(idx):
        j = idx[n + 1] if n + 1 < len(idx) else len(lines)
        blk = lines[i:j]
        while blk and not blk[-1].strip():
            blk.pop()
        out.append((lines[i], blk))
    return base, out


def _base_rules(base_lines):
    out, sec = [], None
    for l in base_lines:
        if l.startswith("## "):
            sec = l[3:].strip().lower(); continue
        s = l.strip()
        if sec == "custom rules" and s.startswith("- ") and not s.startswith("- RULE:") and s not in PLACEHOLDERS:
            out.append(s)
    return list(dict.fromkeys(out))


def merge(old: str, cur: str) -> tuple:
    old_base, old_blocks = _blocks(old)
    cur_lines = cur.rstrip("\n").split("\n")
    cur_set = {l.strip() for l in cur_lines}
    report = {"rules_added": [], "sections_added": [], "left_as_is": []}
    # 1) base custom rules
    want = [r for r in _base_rules(old_base) if r not in cur_set]
    if want:
        if "## Custom rules" not in cur_lines:
            cur_lines += ["", "## Custom rules"]
        i = cur_lines.index("## Custom rules"); j = i + 1
        while j < len(cur_lines) and not cur_lines[j].startswith(("## ", "# ")):
            j += 1
        body = [l for l in cur_lines[i + 1:j] if l.strip() not in PLACEHOLDERS]
        while body and not body[-1].strip():
            body.pop()
        cur_lines = cur_lines[:i + 1] + body + want + ([""] if j < len(cur_lines) else []) + cur_lines[j:]
        report["rules_added"] = [r[2:] for r in want]
    # 2) missing charter / merged-duplicate sections, appended whole
    for marker, blk in old_blocks:
        if marker.strip() in cur_set:
            continue
        cur_lines += [""] + blk
        report["sections_added"].append({"section": marker[3:], "lines": len(blk)})
    # 3) transparency: other base lines that differ are left as is
    for l in old_base:
        s = l.strip()
        if s and s not in cur_set and not s.startswith("- RULE:") and s not in [f"{r}" for r in want] and s not in PLACEHOLDERS:
            report["left_as_is"].append(s[:140])
    if not report["rules_added"] and not report["sections_added"]:
        return cur, report          # nothing to restore: the file is returned byte-identical
    return "\n".join(cur_lines) + "\n", report
