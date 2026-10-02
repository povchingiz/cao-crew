# 2026-10-02 — Zero-Stumble "Ready-to-Fly" Onboarding & Security Hardening

> **Branch:** `master`  
> **Status:** Completed  
> **Source Issue:** [GitHub Issue #1](https://github.com/povchingiz/cao-crew/issues/1)  
> **Cost Optimization Directive:** Delegated bulk code implementation to `opencode` (`zai-org/GLM-5.3-Flash`) to minimize token consumption.

---

## 1. Overview & Objectives

Solve the blockers discovered when installing `cao-crew` on a clean machine:
1. **Security & Privacy:** Eradicate all internal endpoint URLs (`llm.nitec.kz`) and private model references from tracked files and public diagrams. Public template defaults to OpenRouter (`https://openrouter.ai/api/v1`) with generic models.
2. **Model Upgrades for OpenCode:** Configure `zai-org/GLM-5.3` and `zai-org/GLM-5.3-Flash` in `cao.config.local.toml` and sync to `~/.config/opencode/opencode.json` as well as `~/.aws/opencode/opencode.json`.
3. **Assisted Authentication Wizard:** Add an interactive onboarding helper that checks CLI login status (`claude`, `codex`, `agy`) and guides the user through instant login.
4. **Smart Zero-Config Fallback:** If the user lacks an OpenAI-compatible API key, auto-route `coder_worker` to an already-authenticated CLI engine (`claude_code`, `codex`, or `antigravity_cli`) so a full multi-agent squad works with 0 extra keys.
5. **Worker Binary Reconciliations (Hermes & Copilot):** Offer automated installation (`gh extension install github/gh-copilot` / `npm i -g hermes-agent`) or omit missing workers from `profiles.register` so `cao-doctor` stays 100% green.
6. **One-Command Setup:** Provide root-level `./install.sh` tying bootstrap, onboarding wizard, and pre-flight doctor checks together.

---

## 2. Execution Strategy & Worker Delegation

- **Architect & Reviewer (Antigravity):** Planned tasks, orchestrated workflow, verified tests, and performed audits.
- **Primary Implementer (`opencode` - `zai-org/GLM-5.3-Flash`):** Executed file modifications, script authoring, and template scrubbing via `opencode run`.

---

## 3. Work Breakdown & Task Checklist

- [x] **Task 1: Eradicate Internal Endpoint Traces from Public Files**
  - Target files:
    - `setup/2_configure/cao.config.toml` (uses `openrouter`, `https://openrouter.ai/api/v1`, `deepseek/deepseek-chat`)
    - `setup/3_apply/render_config.py` (scrubbed nitec references)
    - `run/cao_config_server.py` (replaced nitec placeholder with openrouter)
    - `wcao/design/cao-architecture.mmd` & `cao-architecture.svg`
    - `wcao/design/cao-map.md`
    - `wcao/design/2026-09-20-autonomous-cao-orchestration-design.md`
  - Real private endpoint lives solely in `setup/2_configure/cao.config.local.toml` (gitignored).

- [x] **Task 2: Sync OpenCode Config to `~/.config/opencode/opencode.json`**
  - Updated `setup/3_apply/render_config.py` so `render_opencode()` renders into both `~/.aws/opencode/opencode.json` and `~/.config/opencode/opencode.json` (preserving user-defined MCPs and keybindings).
  - Configured `zai-org/GLM-5.3` and `zai-org/GLM-5.3-Flash` in `cao.config.local.toml` as requested.

- [x] **Task 3: Assisted Onboarding & Zero-Config Fallback Wizard**
  - Implemented `setup/1_install/onboarding.sh`:
    - Checks auth for `claude`, `codex`, `agy`.
    - Prompts user to log in interactively if unauthenticated.
    - Asks if user has an OpenAI-compatible API key.
    - If Yes: writes endpoint + key to `~/.config/cao/cao.env` and `cao.config.local.toml`.
    - If No: enables Smart Zero-Config by routing `coder_worker` provider to an authenticated CLI engine.
    - Checks for `copilot` and `hermes`: offers install or comments them out of active profile registration.

- [x] **Task 4: Root Executable `./install.sh`**
  - Created `./install.sh` at repo root.
  - Chains: `setup/1_install/bootstrap.sh` -> `setup/1_install/onboarding.sh` -> `./setup/3_apply/apply.sh` -> `run/cao-doctor`.
  - Shows celebratory "🚀 Everything is verified and ready to fly!" banner.

- [x] **Task 5: Verification & Pre-flight Testing**
  - Ran `run/cao-doctor` (18 passed, 0 failed).
  - Ran full test suite: `uv run --with pytest pytest tests/` (58 passed).
  - Verified 0 traces of `llm.nitec.kz` in tracked files.
