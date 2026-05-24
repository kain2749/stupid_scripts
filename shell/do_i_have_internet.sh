#!/usr/bin/env bash

while ! timeout 2 bash -c '</dev/tcp/1.1.1.1/443' >/dev/null 2>&1; do
    echo "nu"
    sleep 2
done

echo "yuh"
