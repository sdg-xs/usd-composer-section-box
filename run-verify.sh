#!/usr/bin/env bash
# Runs the headless model verifier under Kit's Python with USD on the path.
set -euo pipefail
KIT=/c/kit-app-template/_build/windows-x86_64/release/kit
USD=/c/Users/StevenGomba/AppData/Local/ov/data/exts/v2/omni.usd.libs-d9c4035c6b59cdf0
cd "$(dirname "$0")"
PYTHONPATH="$(cygpath -w "$USD")" PATH="$USD/bin:$KIT:$PATH" "$KIT/python/python.exe" "${1:-verify_model.py}"
