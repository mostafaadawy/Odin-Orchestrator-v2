cd /home/mostafa/odin_backups/20261014_083200 && ls -la && for t in *.tgz; do echo "== $t"; tar tzf "$t" | grep -E '(^|/)\.cred' || echo "no .cred inside"; done
