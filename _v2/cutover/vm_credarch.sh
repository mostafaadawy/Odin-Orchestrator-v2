cd /home/mostafa
for f in $(find . -maxdepth 4 \( -path ./bendcore -o -path ./organics -o -path ./RBO-Staging -o -path '*/node_modules' \) -prune -o \( -name '*.tgz' -o -name '*.tar.gz' -o -name '*.tar' -o -name '*.zip' \) -newermt 2026-06-01 -print 2>/dev/null); do
  case "$f" in *.zip) n=$(unzip -l "$f" 2>/dev/null | grep -c '\.cred');; *) n=$(tar tf "$f" 2>/dev/null | grep -c '\.cred');; esac
  [ "$n" != "0" ] && echo "ARCHIVE WITH .cred: $f ($n)"
done; echo "archive scan done"
ls -d anchor-online* odin-web* 2>/dev/null
