# Production Resilience, Watchdog Hardening & Zero-Friction DX

> **Date:** 2026-09-22  
> **Status:** Pending Review / Ready for Execution  
> **Target Milestone:** Milestone 6 (Production Resilience & Zero-Friction Onboarding)  
> **Related Specs:** [`master-plan.md`](master-plan.md), [`now.md`](now.md), [`AGENTS.md`](../../AGENTS.md)  
> **Constraint:** DO NOT git push to remote without explicit user confirmation.

---

## 1. Executive Summary & Root-Cause Analysis

A comprehensive architectural audit of `wcao` identified 6 operational hazards and bottlenecks that limit reliability in production and autonomous execution:

1. **Task Hanging & Stagnation Hazard (`cao_auto.py`)**: The headless DAG runner lacks task timeouts. If an underlying CLI hangs, hits a prompt, or enters an infinite loop, the orchestrator stalls indefinitely.
2. **Interactive CLI Prompt Deadlocks**: Frontier CLIs (`claude`, `codex`, `agy`) query for interactive user confirmation (`[y/N]`) before executing dangerous or new shell commands. In background `tmux` panes, these prompts cause silent deadlocks.
3. **Parallel Race Conditions without Worktrees**: When running parallel tasks on disjoint file sets, workers still share the root directory (`worktree_isolation = false`), causing git index and transient build file collisions.
4. **Port 9889 & Daemon Collision**: Stale daemon processes lock port 9889 after abrupt termination, requiring manual process killing.
5. **Brittle Upstream Monkey-Patch (`pyte`)**: Patching `pyte` directly inside `~/.local/share/uv/tools` is lost on any `uv tool update` or cache purge.
6. **Onboarding Friction for Sparse CLI Environments**: New users with only 1 or 2 tools face configuration warnings for missing engines (`hermes`, `copilot`).

---

## 2. Architecture & Implementation Blueprint

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                                  MILESTONE 6 ROADMAP                                         │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ Phase 1: Watchdog & Stagnation Detection (P0)                                                │
│   ├── TaskTimeoutWatcher: Max wall-clock execution threshold per task (default 900s)         │
│   ├── StagnationSensor: Detect unchanged stdout for > 180s                                   │
│   └── Auto-Kill & Fallback: Auto-terminate hung terminal, notify Telegram, apply L2 fallback │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ Phase 2: CLI Non-Interactive Mode & Prompt Auto-Approval (P0)                                │
│   ├── Configure autonomous flags in worker templates (--dangerously-skip-permissions)        │
│   └── Tmux capture probe: Detect "[y/N]" prompts and automatically respond when isolated     │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ Phase 3: Git Worktree Isolation Engine (P1)                                                  │
│   ├── GitWorktreeManager in run/cao_worktree.py (isolated ephemeral branch per worker)       │
│   ├── Fast-forward disjoint merge gate back to target branch                                 │
│   └── Automatic worktree lifecycle cleanup (pre-run and post-run)                            │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ Phase 4: Port 9889 Self-Healing & Daemon Probe (P1)                                          │
│   ├── Health probe with automatic stale daemon reclamation in cao-run / cao-auto             │
│   └── Dynamic fallback port negotiation (CAO_SERVER_PORT=9889 -> 9890)                      │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ Phase 5: Zero-Friction Onboarding Wizard (cao-init) (P2)                                     │
│   ├── Automated CLI engine discovery (detects installed CLIs & valid API keys)              │
│   ├── Dynamic tailored cao.config.toml generation (only enables available engines)          │
│   └── Automatic compile and apply with 1-click launch readiness                              │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ Phase 6: SQLite Episodic Memory Maintenance & Pruning (P2)                                   │
│   ├── cao-memory prune / vacuum CLI commands for aging and superseded lessons               │
│   └── Relevance decay weighting for BM25 search queries                                      │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Work Breakdown & Verification Gates

### Phase 1: Watchdog & Stagnation Detection (`run/cao_auto.py`)
- **Files to Modify:** [`run/cao_auto.py`](file:///Users/yerta/wcao/run/cao_auto.py), [`tests/test_auto.py`](file:///Users/yerta/wcao/tests/test_auto.py)
- **Implementation:**
  1. In `AutonomousRunner`:
     - Add `task_timeout_seconds: float = 900.0` (15 min) configurable via CLI `--timeout <seconds>`.
     - Add `stagnation_threshold: float = 180.0` (3 min).
  2. In `_poll_active_terminals`:
     - Calculate `elapsed = time.monotonic() - meta["started"]`.
     - Track `meta["last_output_len"]` and `meta["last_activity_time"]`.
     - If `output_len != meta["last_output_len"]`, update `meta["last_activity_time"] = time.monotonic()`.
     - If `elapsed > task_timeout_seconds` OR `(time.monotonic() - meta["last_activity_time"]) > stagnation_threshold`:
       - Log watchdog trigger: `Task {tid} timed out / stagnant after {elapsed:.1f}s`.
       - Grab last 30 lines of terminal output and save in `task["failure_dump"]`.
       - Terminate terminal session: `self.client.delete_terminal(terminal_id)`.
       - Auto-swap or escalate: `apply_fallback(task, "Watchdog timeout")`.
       - Send warning to Telegram.
- **Verification Gate:**
  - Create mock stagnant worker test in `tests/test_auto.py`.
  - Verify task is aborted, fallback is applied, and tasks.json reflects timeout.

### Phase 2: CLI Prompt Deadlock Prevention
- **Files to Modify:** [`setup/2_configure/prompts/*.md`](file:///Users/yerta/wcao/setup/2_configure/prompts/), [`setup/2_configure/cao.config.toml`](file:///Users/yerta/wcao/setup/2_configure/cao.config.toml), [`run/cao_auto.py`](file:///Users/yerta/wcao/run/cao_auto.py)
- **Implementation:**
  1. Ensure autonomous configurations pass non-interactive flags where available.
  2. Add terminal prompt inspector in `run/cao_auto.py`:
     - If output ends with `(?i)\[y/n\]` or `(?i)allow .* \(y\)es / \(n\)o`:
       - If running in automated mode with sandbox active, emit auto-approval `y\n` to stdin via CAO daemon client.
       - Log auto-approval event in task metadata.
- **Verification Gate:**
  - Unit test simulating interactive prompt in terminal buffer, verifying automated resolution.

### Phase 3: Git Worktree Isolation Engine (`run/cao_worktree.py`)
- **Files to Create:** [`run/cao_worktree.py`](file:///Users/yerta/wcao/run/cao_worktree.py), [`tests/test_worktree.py`](file:///Users/yerta/wcao/tests/test_worktree.py)
- **Implementation:**
  1. Class `WorktreeManager`:
     - `create_worktree(repo_root: Path, task_id: str) -> Path`: Runs `git worktree add -b wcao/task-<id> .wcao/worktrees/worker-<id> HEAD`.
     - `merge_worktree(repo_root: Path, task_id: str, target_branch: str) -> bool`: Commits changes in worktree, fast-forwards onto target branch, checks for conflicts.
     - `cleanup_worktree(repo_root: Path, task_id: str) -> None`: Runs `git worktree remove --force` and deletes temporary branch.
  2. Wire `WorktreeManager` into `AutonomousRunner._dispatch_task` when `worktree_isolation = true`.
- **Verification Gate:**
  - Launch 2 concurrent workers editing separate files in separate worktrees; verify clean merge without working tree collision.

### Phase 4: Port 9889 Self-Healing & Daemon Probe
- **Files to Modify:** [`run/cao-run`](file:///Users/yerta/wcao/run/cao-run), [`run/cao-doctor`](file:///Users/yerta/wcao/run/cao-doctor), [`run/cao-stop`](file:///Users/yerta/wcao/run/cao-stop)
- **Implementation:**
  1. In `run/cao-run`:
     - Probe `http://127.0.0.1:9889/health`.
     - If port is bound but health probe returns 5xx or connection refused (zombie process):
       - Find process PID via `lsof -ti :9889`.
       - If owned by current user and matches `cao-server`, gracefully terminate (`kill -TERM` -> 2s -> `kill -KILL`).
       - Clean stale socket before starting server.
  2. Add `cao-doctor --fix` flag to automate pre-flight cleanup without manual shell scripting.
- **Verification Gate:**
  - Test simulated stale socket; verify `cao-run` cleans and launches without error.

### Phase 5: Zero-Friction Onboarding Wizard (`run/cao-init`)
- **Files to Create:** [`run/cao_init.py`](file:///Users/yerta/wcao/run/cao_init.py), [`run/cao-init`](file:///Users/yerta/wcao/run/cao-init), [`tests/test_init.py`](file:///Users/yerta/wcao/tests/test_init.py)
- **Implementation:**
  1. Interactive & headless discovery:
     - Detects presence of `claude`, `codex`, `opencode`, `agy`, `copilot`, `hermes`.
     - Checks authentication status for each tool.
     - Builds optimal `setup/2_configure/cao.config.toml` configuring ONLY detected, authenticated engines.
     - Automatically invokes `./setup/3_apply/apply.sh`.
     - Outputs clear next step: `run/cao-run` or `run/cao-auto "<goal>"`.
- **Verification Gate:**
  - Run `run/cao-init --dry-run` on systems with varying subsets of CLI tools; verify valid tailored configs.

### Phase 6: SQLite Episodic Memory Maintenance (`run/cao_memory.py`)
- **Files to Modify:** [`run/cao_memory.py`](file:///Users/yerta/wcao/run/cao_memory.py), [`run/cao-memory`](file:///Users/yerta/wcao/run/cao-memory), [`tests/test_memory.py`](file:///Users/yerta/wcao/tests/test_memory.py)
- **Implementation:**
  1. Add `prune` subcommand to `run/cao-memory`:
     - Prunes entries older than $N$ days (default 60 days) unless pinned.
     - Removes duplicate summaries using FTS5 match similarity.
  2. Implement `vacuum` subcommand to reclaim SQLite disk space.
- **Verification Gate:**
  - Unit tests verifying prune, deduplication, and search index integrity after vacuum.

---

## 4. Execution Sequence & Safety Controls

| Order | Phase | Focus | Estimated Scope | Rollback Strategy |
|---|---|---|---|---|
| **Step 1** | Phase 1 | Watchdog & Stagnation Detection | `run/cao_auto.py` | Configurable `--timeout 0` disables watchdog |
| **Step 2** | Phase 2 | CLI Non-Interactive Flags & Prompts | Configs & Prompts | Revert to standard prompts |
| **Step 3** | Phase 4 | Port 9889 Self-Healing | `run/cao-run`, `run/cao-stop` | Retain manual `cao-stop` fallback |
| **Step 4** | Phase 5 | `cao-init` Discovery Wizard | New standalone script | Zero impact on existing core |
| **Step 5** | Phase 6 | Memory Pruning & Deduplication | `run/cao_memory.py` | DB backed up to `memory.sqlite.bak` |
| **Step 6** | Phase 3 | Git Worktree Isolation | `run/cao_worktree.py` | Feature flag `worktree_isolation = false` |

> [!CAUTION]
> **Hard Rule:** All changes must pass `uv run --with pytest pytest tests/` with 0 failures before any task is marked done.  
> **Hard Rule:** NO `git push` without prior explicit approval from user.
