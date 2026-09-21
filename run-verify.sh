#!/usr/bin/env bash
# Git Bash entry point using PowerShell 7. Accepts the verifier's arguments.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec pwsh.exe -NoProfile -File "$(cygpath -w "$script_dir/run-verify.ps1")" "$@"
