#!/bin/sh
# Double-click to play. The first run installs the libraries (needs internet, about 1-3 minutes).
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 is not installed. Get it from https://www.python.org/downloads/"
    read -r _
    exit 1
fi
exec python3 main3d.py
