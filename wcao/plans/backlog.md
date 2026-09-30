# backlog.md — wcao future ideas

> Items here are **not planned for immediate implementation**. When something gets prioritized, move it to `master-plan.md` and create a dated spec file.

---

## B1 — Worker Eval Framework
**Why:** Right now we route by token quota and task type heuristics. A proper eval loop would measure actual task completion quality per model (Claude vs DeepSeek vs Hermes) and feed those metrics back into routing decisions.
**How:** Run same task N times across workers, compare output quality with a judge model, update routing weights in `cao.config.toml`.

---

## B2 — Cost Dashboard (per-task spend aggregation)
**Why:** `cao-tokens` gives raw spend; `cao-limits` gives remaining quota. Neither shows cost *per task* or *per session*.
**How:** Tag each worker terminal launch with task ID, capture token deltas from `cao-limits` before/after, write to `wcao/telemetry.jsonl`, expose via `cao-tokens --breakdown`.

---

## B3 — Task Retry & Fallback Reassignment
**Why:** When a worker errors mid-task (crash, timeout, bad output), the task is currently marked FAILED. We should auto-retry on a different worker.
**How:** Add retry count + fallback worker chain in `tasks.json` schema. `cao_auto.py` re-dispatches on ERROR state up to `max_retries` (configurable).

---

## B4 — Structured Output Validation (JSON Schema)
**Why:** Workers return free-text. Supervisors parse it with regex/heuristics. This is fragile.
**How:** Define a JSON schema per task type in `wcao/schemas/`. Validate worker output before marking COMPLETED. Reject and retry on schema mismatch.

---

## B5 — CI/CD for `copilot_worker` *(WIP)*
**Why:** `copilot_worker` is registered and detected by `cao-doctor` but its CI/CD and cloud deploy integration is not yet implemented.
**How:** Wire `gh pr create` + status checks into the worker flow. Let it open PRs and report CI results back to the supervisor.
**Note:** Marked WIP across config and docs — do not remove WIP labels until this is fully implemented.

---

## B6 — Web UI Task Board
**Why:** `cao-monitor` is a terminal TUI. A simple web dashboard would be more accessible and shareable.
**How:** `cao-server` (already running on port 9889) can serve a static HTML page reading from `wcao/tasks.json` via SSE/polling. No framework needed.

---

## B7 — Plugin System for Custom Workers
**Why:** Adding a new worker currently requires editing `render_config.py`, `cao.config.toml`, `cao-doctor`, and prompt templates.
**How:** Define a `[worker.my_worker]` schema in `cao.config.toml` that auto-generates all required artefacts when `./3_apply/apply.sh` is run.
