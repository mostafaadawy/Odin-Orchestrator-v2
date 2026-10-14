#!/bin/bash
# mkroot.sh <name> [full]  — make a THROWAWAY experiment root under _research/tmp/<name> (the only place deletes happen).
# minimal: core code + shared/agents + EMPTY projects  |  full: the whole isolated workspace (for LLM runs)
set -e; export PATH=/usr/bin:/bin:/usr/sbin:/sbin
ISO=/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Isolated; T="$ISO/_research/tmp/$1"
case "$T" in "$ISO/_research/tmp/"?*) [ -e "$T" ] && chmod -R u+w "$T"; rm -rf -- "$T";; *) echo bad; exit 2;; esac
mkdir -p "$T/workspace/projects" "$T/workspace/history" "$T/workspace/logs" "$T/data"
/usr/bin/rsync -a --exclude __pycache__ --exclude '*.bak*' "$ISO/server" "$ISO/orchestrator" "$ISO/CLAUDE.md" "$ISO/README.md" "$T/"
if [ "$2" = "fullall" ]; then
  /usr/bin/rsync -a --exclude __pycache__ --exclude '*.bak*' "$ISO/workspace/" "$T/workspace/"
  /usr/bin/rsync -a --exclude __pycache__ --exclude node_modules "$ISO/dashboard" "$ISO/voice" "$ISO/shells" "$T/"; /usr/bin/rsync -a "$ISO/data/" "$T/data/" 2>/dev/null || true
elif [ "$2" = "full" ]; then
  /usr/bin/rsync -a --exclude __pycache__ --exclude '*.bak*' --exclude 'chats' --exclude 'logs' "$ISO/workspace/" "$T/workspace/"
  /usr/bin/rsync -a --exclude __pycache__ --exclude node_modules "$ISO/dashboard" "$ISO/voice" "$ISO/shells" "$T/"
  chmod -R u+w "$T"; mkdir -p "$T/workspace/chats" "$T/workspace/logs"; /usr/bin/rsync -a "$ISO/data/" "$T/data/" 2>/dev/null || true
else
  /usr/bin/rsync -a "$ISO/workspace/shared" "$ISO/workspace/agents" "$T/workspace/"
  mkdir -p "$T/workspace/projects/_shared" "$T/workspace/chats"
fi
chmod -R u+w "$T"; echo "$T"
