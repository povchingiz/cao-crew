# wcao — Master Plan

> **Last updated:** 2026-09-22
> **Status:** Milestone 6 in progress

---

## Shipped Milestones (M1–M5)

| Milestone | What | Status |
|---|---|---|
| M1–M3 | Provisioner, prompt renderer, MCP inheritance, tmux lifecycle | ✅ Done |
| M4 | `cao-limits`, `cao-auto` DAG dispatcher, Telegram telemetry, 429 fallback | ✅ Done |
| M5 | TokenMaster, `cao-plan`, context compactor, procedural memory, anti-tamper gate | ✅ Done |

56/56 tests passing.

---

## Milestone 6 — Production Resilience & Zero-Friction DX

*Full spec: [`2026-09-22-production-resilience-and-dx.md`](2026-09-22-production-resilience-and-dx.md)*

| ID | Task | Status |
|---|---|---|
| P6.1 | Watchdog & stagnation detection in `cao_auto.py` | 🔲 Todo |
| P6.2 | CLI prompt deadlock prevention (non-interactive flags) | 🔲 Todo |
| P6.3 | Git worktree isolation engine (`cao_worktree.py`) | 🔲 Todo |
| P6.4 | Port 9889 self-healing & zombie daemon reclamation | 🔲 Todo |
| P6.5 | Setup wizard `cao-init` | 🔲 Todo |
| P6.6 | SQLite memory pruning (`cao-memory prune/vacuum`) | 🔲 Todo |

---

## Backlog (Future Ideas)

*See [`backlog.md`](backlog.md) for full descriptions.*

| ID | Idea | Why |
|---|---|---|
| B1 | Worker eval framework | Measure which model does best per task type |
| B2 | Cost dashboard (per-task spend aggregation) | Visibility into token economics |
| B3 | Task retry + fallback reassignment | Resilience when a worker fails mid-task |
| B4 | Structured output validation (JSON schema) | Workers currently return free-text |
| B5 | CI/CD for `copilot_worker` | Automate deploys via GitHub PRs (WIP) |
| B6 | Web UI task board | Visual alternative to `cao-monitor` |
| B7 | Plugin system for custom workers | Add workers via config only |
