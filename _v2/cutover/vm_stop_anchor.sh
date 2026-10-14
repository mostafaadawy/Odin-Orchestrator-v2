sudo systemctl stop odin-anchor-online
sleep 2
echo "odin-anchor-online: $(systemctl is-active odin-anchor-online)"
echo "anchor process left: $(pgrep -fc 'anchor-online/anchor_remote.py')"
echo "odin-web-online: $(systemctl is-active odin-web-online)"
