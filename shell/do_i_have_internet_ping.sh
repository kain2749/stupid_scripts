#!/usr/bin/env bash

while true; do
    if ping -c 1 -W 2 8.8.8.8 >/dev/null 2>&1; then
        echo "yuh"
        exit 0
    fi

    echo "nu"
    sleep 2
done
