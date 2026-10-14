find /home/mostafa/workspace -type f -printf "%p  %s bytes  %TY-%Tm-%Td\n"
ls -la /home/mostafa/odin_backups 2>&1 | head -3
ss -ltn | grep -c ":48619 " 
