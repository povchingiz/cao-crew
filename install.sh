#!/usr/bin/env bash
#
# CAO chained installer — one command from zero to verified squad.
#
#   1. bootstrap.sh   — installs prerequisites, CAO, worker CLIs, renders config
#   2. onboarding.sh  — interactive logins + smart coder_worker routing
#   3. apply.sh       — compiles configs & registers worker profiles
#   4. cao-doctor     — pre-flight health check
#
# Usage:
#   ./install.sh                # full chain (interactive where useful)
#   ./install.sh -y             # forward non-interactive to onboarding
#
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ONBOARD_FLAGS=""
for a in "$@"; do
  case "$a" in
    --non-interactive|-y) ONBOARD_FLAGS="--non-interactive" ;;
    *) ;;
  esac
done

printf '\033[1;36m==>\033[0m 1/4 bootstrap (prereqs, CAO, worker CLIs)...\n'
"$REPO/setup/1_install/bootstrap.sh" "$@"

printf '\033[1;36m==>\033[0m 2/4 onboarding (auth + smart routing)...\n'
"$REPO/setup/1_install/onboarding.sh" $ONBOARD_FLAGS

printf '\033[1;36m==>\033[0m 3/4 apply (compile configs, register profiles)...\n'
"$REPO/setup/3_apply/apply.sh" "$@"

printf '\033[1;36m==>\033[0m 4/4 doctor (pre-flight health check)...\n'
"$REPO/run/cao-doctor"

cat <<'EOF'

============================================================
🚀 Everything is verified and ready to fly!
============================================================

Start with: cao-run
        or: cao-config   (browser config editor)

============================================================
EOF
