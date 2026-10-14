cd /var/log/nginx 2>/dev/null || exit 0
( for f in access.log*; do case "$f" in *.gz) zcat "$f";; *) cat "$f";; esac; done ) 2>/dev/null | grep -E '/odin-(anchor|web)' > /tmp/_odin_req.txt
echo "odin requests total: $(wc -l < /tmp/_odin_req.txt)"
echo "android/Dart clients: $(grep -ciE 'android|dart/|okhttp' /tmp/_odin_req.txt)"
grep -iE 'android|dart/|okhttp' /tmp/_odin_req.txt | awk '{print $1}' | sort | uniq -c | head
echo "iPhone/iOS clients: $(grep -ciE 'iphone|cfnetwork|ios' /tmp/_odin_req.txt)"
rm -f /tmp/_odin_req.txt
