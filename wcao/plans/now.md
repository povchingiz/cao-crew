# now.md — wcao · active focus

> **Branch:** `master`
> **Active Plan:** [`2026-10-02-zero-stumble-onboarding.md`](2026-10-02-zero-stumble-onboarding.md)
> **Rule:** NEVER run `git push` without explicit user confirmation.

---

## ✅ What's Done (Milestones 1–5)

All shipped — see [`archive/`](archive/) for historical specs.

- Core provisioner, prompt renderer, MCP inheritance, tmux lifecycle
- `cao-auto` autonomous DAG dispatcher + Telegram telemetry
- Universal 429 fallback / TokenMaster quota routing
- `cao-limits` CLI — live quota inspector (visual utilization bars)
- Repo root detection, scoped tmux sessions, `cao-stop --project`
- Context compactor (Hermes 50% rule) — `cao_compactor.py`
- Procedural memory (`wcao/skills/`) + SQLite FTS5 episodic memory
- `hermes_worker` engine integration + conformance test suite
- `cao-plan` goal decomposer → cycle-free DAG in `wcao/tasks.json`
- Anti-test-tampering gate (`cao_tamper.py`)
- `cao-run` fix: early symlink resolution prevents `$HERE: unbound variable` crash ([`wcao/plans/2026-09-22-cao-run-fix.md`](2026-09-22-cao-run-fix.md))
- Shorthand supervisor flag: `--sv <engine>` (`agy`, `codex`, `claude`, `opencode`, `hermes`) in `run/cao-run`
- `code_supervisor.md` prompt streamlined to strict orchestration-only mandate
- Configured bulk models for OpenCode (`Kimi-K3`, `GLM-5.3`, `DeepSeek-V4-Pro`)
- 58/58 test suite passing (`tests/test_cao_run_flags.py`)
- Orca ADE architecture comparison & backlog mapped

---

## 🔥 Prioritized Task Queue — Milestone 6: Production Resilience

- [ ] **P6.1 Watchdog & Stagnation Detection** — max 900s wall-clock + 180s stdout stagnation in [`run/cao_auto.py`](../../run/cao_auto.py)
- [ ] **P6.2 CLI Prompt Deadlock Prevention** — non-interactive flags + `[y/N]` auto-responder in worker profiles
- [ ] **P6.4 Port 9889 Self-Healing** — health-check probe + zombie daemon cleanup in [`run/cao-run`](../../run/cao-run)
- [ ] **P6.5 Setup Wizard `cao-init`** — auto-detect CLIs, generate tailored `cao.config.toml`, 1-click compile
- [ ] **P6.6 Memory Pruning** — `cao-memory prune` / `vacuum` subcommands to prevent memory dilution
- [ ] **P6.3 Git Worktree Isolation** — `WorktreeManager` in [`run/cao_worktree.py`](../../run/cao_worktree.py) for parallel workers *(most complex, last)*

---

## 🔮 Backlog: Orca (`stablyai/orca`) Feature Adoptions

- [ ] **Automated Worktree Lifecycle** — Task-level worktree provision (`git worktree add`), branch isolation, and auto-squash merge upon passing verification.
- [ ] **UI Context Capture ("Design Mode")** — Lightweight CLI/browser hook extracting live DOM element, CSS styles, and viewport screenshot directly into `codex_worker` prompt.
- [ ] **TokenMaster Multi-Account Rotation** — Hot-swap API keys/profiles across multiple accounts of the same provider on 429 before cross-tier downgrade.
- [ ] **Remote SSH Worktree Workers** — Run heavy workers (e.g. local vLLM / Hermes) on remote GPU machines over SSH worktrees while managing locally.

