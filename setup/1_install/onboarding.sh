#!/usr/bin/env bash
#
# CAO onboarding — interactive auth & configuration wizard.
# Complements bootstrap.sh (which installs binaries): this script makes sure
# every engine is LOGGED IN and the coder_worker is routed somewhere that works.
#
# Usage:
#   ./setup/1_install/onboarding.sh                 # interactive
#   ./setup/1_install/onboarding.sh --non-interactive
#   ./setup/1_install/onboarding.sh -y              # non-interactive defaults
#
set -euo pipefail

# --- resolve repo root -------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIGURE="$REPO/setup/2_configure"
LOCAL_TOML="$CONFIGURE/cao.config.local.toml"
CAO_ENV="$HOME/.config/cao/cao.env"

# --- interactivity -----------------------------------------------------------
NON_INTERACTIVE=0
for a in "$@"; do
  case "$a" in
    --non-interactive|-y) NON_INTERACTIVE=1 ;;
    *) ;;
  esac
done
# not a TTY -> force non-interactive
if [ ! -t 0 ]; then
  NON_INTERACTIVE=1
fi

# --- colored output helpers --------------------------------------------------
if [ -t 1 ]; then
  C_BLUE=$'\033[1;36m'; C_YEL=$'\033[1;33m'; C_GRN=$'\033[1;32m'; C_RED=$'\033[1;31m'; C_OFF=$'\033[0m'
else
  C_BLUE=""; C_YEL=""; C_GRN=""; C_RED=""; C_OFF=""
fi
log()  { printf '%s==>%s %s\n' "$C_BLUE" "$C_OFF" "$*"; }
ok()   { printf '%s[ok]%s %s\n' "$C_GRN" "$C_OFF" "$*"; }
warn() { printf '%s[!]%s %s\n' "$C_YEL" "$C_OFF" "$*"; }
bad()  { printf '%s[x]%s %s\n' "$C_RED" "$C_OFF" "$*"; }

# prompt_yn QUESTION DEFAULT(yes|no) -> returns 0 if yes, 1 if no.
# In non-interactive mode always answers with the default without asking.
prompt_yn() {
  local question="$1" default="$2" answer
  if [ "$NON_INTERACTIVE" = "1" ]; then
    [ "$default" = "yes" ] && return 0 || return 1
  fi
  if [ "$default" = "yes" ]; then
    printf '%s[?]%s %s [Y/n] ' "$C_BLUE" "$C_OFF" "$question" > /dev/tty
  else
    printf '%s[?]%s %s [y/N] ' "$C_BLUE" "$C_OFF" "$question" > /dev/tty
  fi
  read -r answer < /dev/tty || return 1
  case "$answer" in
    "") [ "$default" = "yes" ] && return 0 || return 1 ;;
    [Yy]|[Yy][Ee][Ss]) return 0 ;;
    *) return 1 ;;
  esac
}

# read a line with default; in non-interactive mode returns the default.
prompt_value() {
  local label="$1" default="$2" val
  if [ "$NON_INTERACTIVE" = "1" ]; then
    printf '%s' "$default"
    return 0
  fi
  printf '%s [%s]: ' "$label" "$default" > /dev/tty
  read -r val < /dev/tty || val=""
  printf '%s' "${val:-$default}"
}

# ============================================================================
log "CAO onboarding — checking engine authentication & routing"
[ "$NON_INTERACTIVE" = "1" ] && warn "non-interactive mode: prompts skipped, defaults applied"

# interactive_login CMD... — run an interactive login command only when a TTY is
# available; otherwise skip (login wizards need stdin, never run them blind).
interactive_login() {
  if [ "$NON_INTERACTIVE" = "1" ] || [ ! -t 0 ]; then
    warn "Non-interactive — skipping login wizard. Run it manually later."
    return 0
  fi
  "$@"
}

# ============================================================================
# Section A — Auth checks: Claude, Codex, Antigravity
# ============================================================================
log "Section A: auth checks"

# --- Claude ------------------------------------------------------------------
if command -v claude >/dev/null 2>&1; then
  if CLAUDE_NONINTERACTIVE=1 claude auth status >/dev/null 2>&1; then
    ok "Claude Code authenticated"
  else
    if prompt_yn "Claude Code is unauthenticated. Log in now?" yes; then
      log "Launching claude — complete /login inside the session, then exit."
      interactive_login claude || warn "claude exited — login may not have completed"
    else
      warn "Skipping Claude login — claude_worker/supervisor may fail until you run 'claude'."
    fi
  fi
else
  warn "claude CLI not found — run bootstrap.sh first"
fi

# --- Codex -------------------------------------------------------------------
if command -v codex >/dev/null 2>&1; then
  if codex login status >/dev/null 2>&1; then
    ok "OpenAI Codex authenticated"
  else
    if prompt_yn "OpenAI Codex is unauthenticated. Log in now?" yes; then
      interactive_login codex login || warn "codex login did not complete"
    else
      warn "Skipping Codex login — codex_worker may fail until you run 'codex login'."
    fi
  fi
else
  warn "codex CLI not found — run bootstrap.sh first"
fi

# --- Antigravity -------------------------------------------------------------
AGY_ONB="$HOME/.gemini/antigravity-cli/cache/onboarding.json"
if command -v agy >/dev/null 2>&1; then
  if [ -f "$AGY_ONB" ] && grep -q '"onboardingComplete": *true' "$AGY_ONB" 2>/dev/null; then
    ok "Antigravity onboarded"
  else
    if prompt_yn "Antigravity is not onboarded. Run agy now?" yes; then
      interactive_login agy || warn "agy exited — onboarding may not have completed"
    else
      warn "Skipping Antigravity onboarding — analyst/QA workers may fail until you run 'agy'."
    fi
  fi
else
  warn "agy CLI not found — run bootstrap.sh first"
fi

# ============================================================================
# Section B — Copilot & Hermes
# ============================================================================
log "Section B: Copilot & Hermes"

if ! command -v copilot >/dev/null 2>&1; then
  if command -v gh >/dev/null 2>&1; then
    if prompt_yn "GitHub Copilot CLI extension is missing. Install via gh extension?" no; then
      gh extension install github/gh-copilot && ok "gh-copilot installed" || warn "gh-copilot install failed"
    fi
  else
    warn "copilot missing and gh CLI not found — skipping Copilot setup"
  fi
else
  ok "copilot CLI present"
fi

if ! command -v hermes >/dev/null 2>&1; then
  if prompt_yn "hermes CLI is missing. Install hermes-agent via npm?" no; then
    npm i -g hermes-agent && ok "hermes-agent installed" || warn "hermes-agent install failed"
  fi
else
  ok "hermes CLI present"
fi

# ============================================================================
# Section C — OpenCode endpoint & Smart Zero-Config Fallback
# ============================================================================
log "Section C: coder_worker endpoint"

have_api_key() {
  [ -n "${CAO_TEST_NO_KEY:-}" ] && return 1
  [ -n "${LOCAL_API_KEY:-}" ] && return 0
  if [ -f "$CAO_ENV" ] && grep -q '^LOCAL_API_KEY=..*' "$CAO_ENV" 2>/dev/null; then return 0; fi
  if [ -f "$REPO/.env" ] && grep -q '^LOCAL_API_KEY=..*' "$REPO/.env" 2>/dev/null; then return 0; fi
  return 1
}

# ensure_local_toml: make sure cao.config.local.toml exists with [endpoint] +
# workers.coder_worker provider/model sections. Reuses the committed template
# as the base so all other workers keep their definitions.
ensure_local_toml() {
  mkdir -p "$CONFIGURE"
  if [ ! -f "$LOCAL_TOML" ]; then
    cp "$CONFIGURE/cao.config.toml" "$LOCAL_TOML"
  fi
}

# set local endpoint (base_url, model) in cao.config.local.toml [endpoint] and
# point coder_worker (opencode_cli) at it. Line-based (no regex) so it survives
# multi-line `models = [` arrays and quoted values.
set_local_endpoint() {
  local base_url="$1" model="$2"
  python3 - "$LOCAL_TOML" "$base_url" "$model" <<'PY'
import sys
path, base_url, model = sys.argv[1], sys.argv[2], sys.argv[3]
lines = open(path).read().split("\n")

def set_kv(lines, section, key, value):
    out, inside, replaced = [], False, False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if inside and not replaced:
                out.append('%s = "%s"' % (key, value)); replaced = True
            inside = (stripped == "[%s]" % section)
        elif inside and not replaced and "=" in stripped and stripped.split("=")[0].strip() == key:
            line = '%s = "%s"' % (key, value); replaced = True
        out.append(line)
    if inside and not replaced:
        out.append('%s = "%s"' % (key, value))
    return out

# replace the whole models array with a single-entry list for the chosen model
def set_models_array(lines, section, model):
    out, inside, in_array, done = [], False, False, False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if in_array:  # array never closed before next section -> close it
                out.append(']')
                in_array, done = False, True
            inside = (stripped == "[%s]" % section)
            out.append(line)
            continue
        if in_array:
            if "]" in stripped:
                out.append('models = ["%s"]' % model)
                in_array, done = False, True
            # drop old array lines
            continue
        if inside and not done and stripped.startswith("models") and "[" in stripped:
            if "]" in stripped:
                out.append('models = ["%s"]' % model)
                done = True
            else:
                in_array = True  # multi-line array: skip until close
            continue
        out.append(line)
    return out

lines = set_kv(lines, "endpoint", "base_url", base_url)
lines = set_models_array(lines, "endpoint", model)
lines = set_kv(lines, "endpoint", "default_model", model)
lines = set_kv(lines, "workers.coder_worker", "model", model)
open(path, "w").write("\n".join(lines))
PY
}

if have_api_key; then
  ok "LOCAL_API_KEY already configured (env / $CAO_ENV / repo .env)"
  # still make sure local toml exists so apply.sh has a target
  [ -f "$LOCAL_TOML" ] || ensure_local_toml
else
  if [ "$NON_INTERACTIVE" = "1" ]; then
    warn "No LOCAL_API_KEY found and running non-interactively — falling back to Smart Zero-Config."
    ZERO_CONFIG=1
  else
    if prompt_yn "Do you have an OpenAI-compatible API key (OpenRouter, DeepSeek, Ollama)?" no; then
      BASE_URL="$(prompt_value "Base URL" "https://openrouter.ai/api/v1")"
      MODEL_ID="$(prompt_value "Model ID" "deepseek/deepseek-chat")"
      API_KEY="$(prompt_value "API key (LOCAL_API_KEY)" "")"
      if [ -z "$API_KEY" ]; then
        bad "No API key entered — falling back to Smart Zero-Config."
        ZERO_CONFIG=1
      else
        mkdir -p "$(dirname "$CAO_ENV")"
        ( umask 077; printf 'LOCAL_API_KEY=%s\n' "$API_KEY" > "$CAO_ENV" )
        chmod 600 "$CAO_ENV"
        ok "LOCAL_API_KEY saved to $CAO_ENV (chmod 600)"
        ensure_local_toml
        set_local_endpoint "$BASE_URL" "$MODEL_ID"
        ok "cao.config.local.toml endpoint: $BASE_URL (model: $MODEL_ID)"
        ZERO_CONFIG=0
      fi
    else
      ZERO_CONFIG=1
    fi
  fi

  if [ "${ZERO_CONFIG:-0}" = "1" ]; then
    # Smart Zero-Config Fallback: route coder_worker at the first engine that
    # is already authenticated — no extra keys needed.
    FALLBACK_ENGINE=""
    for engine in claude_code codex antigravity_cli; do
      case "$engine" in
        claude_code)
          if command -v claude >/dev/null 2>&1 && CLAUDE_NONINTERACTIVE=1 claude auth status >/dev/null 2>&1; then
            FALLBACK_ENGINE="claude_code"; break
          fi ;;
        codex)
          if command -v codex >/dev/null 2>&1 && codex login status >/dev/null 2>&1; then
            FALLBACK_ENGINE="codex"; break
          fi ;;
        antigravity_cli)
          if command -v agy >/dev/null 2>&1 && [ -f "$AGY_ONB" ] && grep -q '"onboardingComplete": *true' "$AGY_ONB" 2>/dev/null; then
            FALLBACK_ENGINE="antigravity_cli"; break
          fi ;;
      esac
    done

    if [ -z "$FALLBACK_ENGINE" ]; then
      bad "No authenticated engine found (claude/codex/agy). Complete at least one login and re-run onboarding."
      exit 1
    fi

    ensure_local_toml
    python3 - "$LOCAL_TOML" "$FALLBACK_ENGINE" <<'PY'
import sys
path, engine = sys.argv[1], sys.argv[2]
lines = open(path).read().split("\n")

def set_in_section(lines, section, key, value):
    out, inside, replaced = [], False, False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if inside and not replaced:
                out.append('%s = "%s"' % (key, value)); replaced = True
            inside = (stripped == "[%s]" % section)
        elif inside and not replaced and "=" in stripped and stripped.split("=")[0].strip() == key:
            line = '%s = "%s"' % (key, value); replaced = True
        out.append(line)
    if inside and not replaced:
        out.append('%s = "%s"' % (key, value))
    return out

lines = set_in_section(lines, "workers.coder_worker", "provider", engine)
open(path, "w").write("\n".join(lines))
PY
    log "[Smart Zero-Config] Coder worker mapped to $FALLBACK_ENGINE. Multi-agent squad ready with 0 extra keys!"
  fi
fi

# ============================================================================
log "Onboarding complete. Next: ./setup/3_apply/apply.sh (or install.sh, which runs everything)."
