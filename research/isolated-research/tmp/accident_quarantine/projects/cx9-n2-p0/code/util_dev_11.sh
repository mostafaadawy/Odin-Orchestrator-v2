# shared helper
retry(){ for i in 1 2 3; do "$@" && return 0; sleep 1; done; return 1; }
