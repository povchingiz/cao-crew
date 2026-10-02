#!/usr/bin/env bash
# update.sh — thin wrapper; forwards everything to run/cao-update.
set -euo pipefail
exec "$(dirname "$0")/run/cao-update" "$@"
