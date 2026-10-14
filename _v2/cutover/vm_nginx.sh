sudo -S -p "" true
sudo nginx -T 2>/dev/null | grep -nE "server_name|root |alias |location |proxy_pass" | grep -iE "odin|anchor|4861|4862|/home/mostafa|server_name" | head -40
