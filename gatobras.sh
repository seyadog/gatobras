#!/bin/sh
# Funciona en Linux y macOS (sin readlink -f, que el macOS antiguo no trae)
d="$0"; [ -L "$d" ] && d="$(readlink "$d")"
cd "$(dirname "$d")" && exec .venv/bin/python -m gatobras "$@"
