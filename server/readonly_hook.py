#!/usr/bin/env python3
"""PreToolUse hook for Claude Code — enforces READ-ONLY mode at the engine level.

Blocks state-changing commands (writes, installs, migrations, deploys, VCS mutations,
service/VM control). Read-only inspection is allowed, INCLUDING read-only redirects to
/dev/null, /dev/std*, fd dups (2>&1), and scratch under /tmp | /var/tmp.
"""
import sys
import json
import re

DENY = [
    # file-output redirection handled by _has_unsafe_redirect (allows /dev/null, /tmp scratch, fd dups)
    r"\brm\b", r"\bmv\b", r"\bcp\b", r"\btee\b", r"\bdd\b", r"\btruncate\b",
    r"\bsed\b[^|]*\s-i", r"\bperl\b[^|]*\s-i",
    r"\bmkdir\b", r"\btouch\b", r"\bln\b", r"\bchmod\b", r"\bchown\b", r"\bchgrp\b",
    r"\bnpm\b\s+(i\b|install|ci\b|run\s+build|rebuild|publish|link)",
    r"\byarn\b\s+(add|install|build)", r"\bpnpm\b\s+(i\b|install|add|build)",
    r"\beslint\b[^|]*--fix", r"\bprettier\b[^|]*(--write|\s-w\b)",
    r"\bnpm\b\s+run\s+lint\b",
    r"\bnpx\b\s+prisma", r"\bprisma\b\s+(migrate|db\s+push|generate|reset)",
    r"\bgit\b\s+(push|commit|reset|checkout|clean|rm\b|add\b|merge|rebase|stash|apply|restore)",
    r"\bsystemctl\b\s+(start|stop|restart|reload|enable|disable)", r"\bservice\b\s+\S+\s+(start|stop|restart)",
    r"\bsudo\b", r"\breboot\b", r"\bshutdown\b", r"\bhalt\b", r"\bpoweroff\b", r"\bkill\b", r"\bkillall\b",
    r"\bdocker\b\s+(run|rm|build|compose|exec|stop|start|restart)",
    r"\bpm2\b\s+(restart|start|stop|reload|delete|save)",
    r"\bscp\b", r"\bsftp\b",
    r"\brsync\b(?!.*(--dry-run|\s-\w*n))",
    r"\baz\b[^|]*vm\s+run-command\s+invoke",
    r"\baz\b\s+\w[\w-]*\s+\w[\w-]*\s+(create|update|delete|set|restart|deallocate|start|stop|add|remove)",
    r"\bcurl\b[^|]*\s-(X|-request)\s*(POST|PUT|DELETE|PATCH)",
    r"\bwget\b[^|]*\s-O",
]
_RX = [re.compile(p, re.IGNORECASE) for p in DENY]

_REDIR = re.compile(r"\d*>>?")
_SAFE_REDIR_TARGETS = ("/dev/null", "/dev/stdout", "/dev/stderr", "/tmp/", "/var/tmp/")


def _has_unsafe_redirect(cmd):
    """A redirect writes state ONLY when its target is a real file. Redirects to /dev/null,
    /dev/std*, an fd dup (>&N), or scratch under /tmp | /var/tmp are read-only-safe — so
    2>/dev/null and a read-only 'psql SELECT ... > /tmp/x' work during read-only diagnosis."""
    for m in _REDIR.finditer(cmd):
        rest = cmd[m.end():].lstrip()
        if rest[:1] in ("'", '"'):
            rest = rest[1:]
        if rest[:1] == "&":
            continue
        if any(rest.startswith(t) for t in _SAFE_REDIR_TARGETS):
            continue
        return True
    return False


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    cmd = ((data.get("tool_input") or {}).get("command") or "")
    if not cmd:
        sys.exit(0)
    if _has_unsafe_redirect(cmd):
        sys.stderr.write(
            "READ-ONLY MODE — this command redirects output to a real file (a write) and is blocked. "
            "Read-only redirects to /dev/null or /tmp scratch are allowed; propose real writes for approval.")
        sys.exit(2)
    for rx in _RX:
        if rx.search(cmd):
            sys.stderr.write(
                "READ-ONLY MODE — this command changes state (write/install/migrate/deploy/VM/"
                "service) and is blocked. Do NOT try to work around it (no alternate shell tricks). "
                "Instead, PROPOSE the exact file edits and/or commands for the owner's approval, then "
                "stop and report.")
            sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
