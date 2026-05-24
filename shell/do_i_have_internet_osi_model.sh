#!/usr/bin/env bash

set -u

fail=0

check() {
    local name="$1"
    shift

    if "$@" >/dev/null 2>&1; then
        printf '[ok]   %s\n' "$name"
    else
        printf '[fail] %s\n' "$name"
        fail=1
    fi
}

check "default route exists" \
    ip route get 1.1.1.1

check "icmp packet out/back" \
    ping -q -n -c 1 -W 2 8.8.8.8

check "dns resolves name" \
    getent hosts example.com

check "tcp 443 handshake works" \
    timeout 3 bash -c '</dev/tcp/1.1.1.1/443'

check "https request works" \
    curl -fsS --max-time 5 https://example.com

if (( fail == 0 )); then
    echo "internet: yuh"
    exit 0
else
    echo "internet: nu"
    exit 1
fi
