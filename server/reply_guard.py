"""PC-2 / F-16 (owner 2026-10-12: REQUIRED) — generic-reply detector and wrong-format handling.

generic_reply(reply, task) -> '' or the reason. A step reply is GENERIC when it shows no concrete work:
  * empty or a single short line;
  * boilerplate ("I'll help", "task completed", "let me know if …") with NO evidence;
  * mostly a restatement of the task with NO evidence.
Evidence = any of: a file path or file name with an extension, a code / proposal block, a shell command, a URL,
a number with a unit or an HTTP/exit code, a KEY_REQUEST line, a JSON object. A generic reply can never PASS a
step (it becomes NOT_DONE, with the reason). Wrong format: callers that need JSON or the VERDICT line get ONE
correction retry (projects.json_retry / verdict_retry) before the existing safe default applies."""
from __future__ import annotations
import re

_BOILER = re.compile(r"\b(i'?ll (help|look|do|handle|take care)|i (have|'ve) (completed|finished|done)|task (is )?(completed|done)"
                     r"|all done|here(?:'s| is) (a|the) summary|let me know if|feel free to|as an ai|i can help|"
                     r"happy to help|i will (now )?(proceed|start|begin)|sure[,!.]|certainly[,!.]|done\.)", re.I)
_EVIDENCE = [
    re.compile(r"```"),                                                        # code / proposal block
    re.compile(r"(?:^|[\s(`'\"])(?:[\w.~-]+/)+[\w.-]+"),                       # a path
    re.compile(r"\b[\w-]+\.(py|js|ts|tsx|jsx|dart|sh|json|md|yml|yaml|sql|html|css|txt|cfg|conf|toml|env\.example)\b", re.I),
    re.compile(r"(?:^|\n)\s*(\$ |npm |npx |python3? |pip |git |curl |bash |node |flutter |prisma |ssh |az )"),
    re.compile(r"https?://\S+"),
    re.compile(r"\b(HTTP|status|exit(?: code)?)\s*[:=]?\s*\d{3}\b|\bexit (code )?\d+\b|\b\d+\s?(ms|s|sec|KB|MB|GB|%|files?|tests?|rows?|lines?)\b", re.I),
    re.compile(r"KEY_REQUEST:"),
    re.compile(r"\{\s*\"[\w-]+\"\s*:"),
]
_WORD = re.compile(r"[a-z0-9]+")


def has_evidence(text: str) -> bool:
    return any(p.search(text or "") for p in _EVIDENCE)


def generic_reply(reply, task: str = "") -> str:
    t = (reply or "").strip()
    if not t:
        return "empty reply"
    if has_evidence(t):
        return ""
    if len(t) < 40 and "\n" not in t:
        return "a single short line with no concrete work"
    if _BOILER.search(t):
        return "boilerplate with no evidence (no file, command, output or result)"
    rw = _WORD.findall(t.lower()); tw = set(_WORD.findall((task or "").lower()))
    if rw and tw and sum(w in tw for w in rw) / len(rw) >= 0.8:
        return "restates the task with no evidence"
    return ""
