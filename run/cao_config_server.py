#!/usr/bin/env python3
"""
cao_config_server.py — Standalone wcao browser-based config editor.
Usage: python3 cao_config_server.py <repo_root>
Serves on http://localhost:9877
No pip dependencies — stdlib only.
"""
import http.server
import json
import os
import re
import subprocess
import sys
import threading
import time
import tomllib
import urllib.parse
from pathlib import Path

PORT = 9877
INACTIVITY_TIMEOUT = 60  # seconds

# ---------------------------------------------------------------------------
# HTML template (self-contained, dark theme)
# ---------------------------------------------------------------------------
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>wcao Config Editor</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #0d1117;
    --surface: #161b22;
    --border: #30363d;
    --text: #e6edf3;
    --muted: #8b949e;
    --accent: #58a6ff;
    --green: #3fb950;
    --red: #f85149;
    --yellow: #d29922;
    --input-bg: #0d1117;
  }
  body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 14px; line-height: 1.5; }
  .container { max-width: 860px; margin: 0 auto; padding: 32px 24px 80px; }
  h1 { font-size: 22px; font-weight: 700; color: var(--accent); margin-bottom: 4px; }
  .subtitle { color: var(--muted); font-size: 12px; margin-bottom: 28px; }
  .file-badge { display: inline-block; background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 3px 8px; font-size: 11px; font-family: monospace; color: var(--muted); margin: 2px 4px 2px 0; }
  .section { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 20px 24px; margin-bottom: 20px; }
  .section h2 { font-size: 14px; font-weight: 600; letter-spacing: .5px; text-transform: uppercase; color: var(--muted); margin-bottom: 16px; border-bottom: 1px solid var(--border); padding-bottom: 8px; }
  .field { margin-bottom: 14px; }
  .field:last-child { margin-bottom: 0; }
  label { display: block; font-size: 12px; font-weight: 600; color: var(--muted); margin-bottom: 4px; letter-spacing: .4px; text-transform: uppercase; }
  input[type=text], input[type=number], input[type=password], textarea, select {
    width: 100%; background: var(--input-bg); border: 1px solid var(--border); border-radius: 6px;
    color: var(--text); padding: 8px 10px; font-size: 13px; font-family: monospace;
    outline: none; transition: border-color .15s;
  }
  input[type=text]:focus, input[type=number]:focus, input[type=password]:focus, textarea:focus, select:focus { border-color: var(--accent); }
  select { appearance: none; cursor: pointer; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath fill='%238b949e' d='M6 8L0 0h12z'/%3E%3C/svg%3E"); background-repeat: no-repeat; background-position: right 10px center; padding-right: 28px; }
  textarea { resize: vertical; min-height: 80px; }
  .row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th { text-align: left; color: var(--muted); font-weight: 600; padding: 6px 10px; border-bottom: 1px solid var(--border); }
  td { padding: 7px 10px; border-bottom: 1px solid var(--border); vertical-align: top; }
  tr:last-child td { border-bottom: none; }
  td.worker-name { font-family: monospace; color: var(--accent); }
  td.provider { color: var(--green); }
  td.focus { color: var(--muted); font-size: 11px; }
  .actions { display: flex; gap: 12px; align-items: center; margin-top: 24px; }
  button { border: none; border-radius: 7px; font-size: 14px; font-weight: 600; cursor: pointer; padding: 10px 22px; transition: opacity .15s, background .15s; }
  #btn-save { background: var(--accent); color: #000; }
  #btn-save:hover { opacity: .85; }
  #btn-save:disabled { opacity: .5; cursor: default; }
  #btn-done { background: transparent; border: 1px solid var(--border); color: var(--muted); }
  #btn-done:hover { border-color: var(--red); color: var(--red); }
  .spinner { display: none; width: 18px; height: 18px; border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin .7s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  #output { display: none; background: #010409; border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-top: 20px; font-family: monospace; font-size: 12px; white-space: pre-wrap; max-height: 340px; overflow-y: auto; color: #7ee787; line-height: 1.6; }
  .status-ok  { color: var(--green); font-weight: 700; }
  .status-err { color: var(--red); font-weight: 700; }
  .hint { font-size: 11px; color: var(--muted); margin-top: 3px; }
</style>
</head>
<body>
<div class="container">
  <h1>⚙ wcao Config Editor</h1>
  <div class="subtitle">Editing config files directly in your browser — changes take effect immediately via apply.sh</div>
  <div style="margin-bottom: 20px;">
    <span class="file-badge">__ENV_PATH__</span>
    <span class="file-badge">__LOCAL_TOML_PATH__</span>
  </div>

  <!-- SECRETS -->
  <div class="section">
    <h2>🔑 Secrets (.env)</h2>
    <div class="field">
      <label>LOCAL_API_KEY</label>
      <input type="password" id="local_api_key" placeholder="sk-..." value="__LOCAL_API_KEY__" autocomplete="off">
      <div class="hint">Bulk worker endpoint key. Stored in <code>.env</code> only — never in the TOML.</div>
    </div>
  </div>

  <!-- ENDPOINT -->
  <div class="section">
    <h2>🌐 Endpoint ([endpoint])</h2>
    <div class="row">
      <div class="field">
        <label>Name</label>
        <input type="text" id="endpoint_name" value="__ENDPOINT_NAME__" placeholder="nitec">
      </div>
      <div class="field">
        <label>Base URL</label>
        <input type="text" id="base_url" value="__BASE_URL__" placeholder="https://api.openrouter.ai/v1">
      </div>
    </div>
    <div class="field">
      <label>Models (one per line)</label>
      <textarea id="models" rows="4" onchange="syncModelSelects()" oninput="syncModelSelects()">__MODELS__</textarea>
      <div class="hint">Exact model IDs as the endpoint lists them.</div>
    </div>
    <div class="field">
      <label>Default Model</label>
      <select id="default_model">__DEFAULT_MODEL_OPTIONS__</select>
    </div>
  </div>

  <!-- ORCHESTRATOR -->
  <div class="section">
    <h2>🎛 Orchestrator ([orchestrator])</h2>
    <div class="row">
      <div class="field">
        <label>Server Port</label>
        <input type="number" id="server_port" value="__SERVER_PORT__" min="1024" max="65535">
      </div>
      <div class="field">
        <label>Max Concurrent Workers</label>
        <input type="number" id="max_concurrent_workers" value="__MAX_WORKERS__" min="1" max="32">
      </div>
    </div>
  </div>

  <!-- WORKERS -->
  <div class="section">
    <h2>👷 Workers</h2>
    <div class="field">
      <label>Coder Worker Model <span style="font-weight:400;text-transform:none;color:var(--muted)">(opencode_cli bulk model)</span></label>
      <select id="coder_model">__CODER_MODEL_OPTIONS__</select>
      <div class="hint">Must be one of the endpoint models above. Updates automatically when you change the models list.</div>
    </div>
    <table>
      <thead><tr><th>Worker</th><th>Provider</th><th>Focus</th></tr></thead>
      <tbody>__WORKERS_TABLE__</tbody>
    </table>
  </div>

  <!-- ACTIONS -->
  <div class="actions">
    <button id="btn-save" onclick="saveConfig()">💾 Save &amp; Apply</button>
    <button id="btn-done" onclick="shutdown()">✓ Done</button>
    <div class="spinner" id="spinner"></div>
    <span id="status-text"></span>
  </div>
  <div id="output"></div>
</div>

<script>
function val(id) { return document.getElementById(id).value.trim(); }

function syncModelSelects() {
  const raw = document.getElementById('models').value;
  const models = raw.split('\n').map(s => s.trim()).filter(Boolean);
  ['default_model', 'coder_model'].forEach(function(id) {
    const sel = document.getElementById(id);
    if (!sel || sel.tagName !== 'SELECT') return;
    const current = sel.value;
    sel.innerHTML = models.map(m =>
      `<option value="${escAttr(m)}"${m === current ? ' selected' : ''}>${escHtml(m)}</option>`
    ).join('');
    // If previous selection gone, pick first
    if (!models.includes(sel.value) && models.length) sel.value = models[0];
  });
}

function escAttr(s) { return s.replace(/"/g, '&quot;'); }

async function saveConfig() {
  const btn = document.getElementById('btn-save');
  const spinner = document.getElementById('spinner');
  const out = document.getElementById('output');
  const statusText = document.getElementById('status-text');

  btn.disabled = true;
  spinner.style.display = 'block';
  out.style.display = 'none';
  statusText.textContent = '';

  const payload = {
    local_api_key:          val('local_api_key'),
    endpoint_name:          val('endpoint_name'),
    endpoint_url:           val('base_url'),
    models:                 val('models'),
    default_model:          val('default_model'),
    coder_model:            val('coder_model'),
    server_port:            parseInt(val('server_port'), 10) || 9889,
    max_concurrent_workers: parseInt(val('max_concurrent_workers'), 10) || 4,
  };

  try {
    const resp = await fetch('/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    out.style.display = 'block';
    if (data.ok) {
      out.innerHTML = '<span class="status-ok">✓ Saved &amp; Applied successfully</span>\n\n' + escHtml(data.output);
      statusText.innerHTML = '<span class="status-ok">✓ Done</span>';
    } else {
      out.innerHTML = '<span class="status-err">✗ Error</span>\n\n' + escHtml(data.output || data.error || 'Unknown error');
      statusText.innerHTML = '<span class="status-err">✗ Failed</span>';
    }
  } catch (e) {
    out.style.display = 'block';
    out.innerHTML = '<span class="status-err">✗ Network error: ' + escHtml(String(e)) + '</span>';
    statusText.innerHTML = '<span class="status-err">✗ Failed</span>';
  } finally {
    btn.disabled = false;
    spinner.style.display = 'none';
  }
}

async function shutdown() {
  if (!confirm('Close the config server? (You can reopen it with run/cao-config)')) return;
  try { await fetch('/shutdown', { method: 'POST' }); } catch(_) {}
  document.body.innerHTML = '<div style="padding:60px; text-align:center; color:#8b949e; font-family:monospace;">Config server closed. You can close this tab.</div>';
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
</script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def read_local_toml(path: Path) -> dict:
    """Read cao.config.local.toml; return empty dict if missing."""
    if not path.exists():
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


def read_env(env_path: Path) -> str:
    """Return LOCAL_API_KEY value from .env file, or empty string."""
    if not env_path.exists():
        return ""
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("LOCAL_API_KEY=") and not line.startswith("#"):
                val = line[len("LOCAL_API_KEY="):].strip()
                # strip optional surrounding quotes
                return val.strip("'\"")
    return ""


def write_env(env_path: Path, api_key: str) -> None:
    """Write (or update) LOCAL_API_KEY in .env, preserving other lines."""
    lines: list[str] = []
    found = False
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if re.match(r"^LOCAL_API_KEY=", line.rstrip()):
                    if api_key:
                        lines.append(f"LOCAL_API_KEY={api_key}\n")
                    # if api_key is empty string, skip (remove) the line
                    found = True
                else:
                    lines.append(line if line.endswith("\n") else line + "\n")
    if not found and api_key:
        lines.append(f"LOCAL_API_KEY={api_key}\n")
    with open(env_path, "w") as f:
        f.writelines(lines)


def _q(s: str) -> str:
    """Return a TOML-safe double-quoted string."""
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def write_local_toml(path: Path, data: dict, models: list[str]) -> None:
    """
    Regenerate cao.config.local.toml from the submitted form data.
    Workers and profiles are read from the base cao.config.toml so we never
    propagate corrupted/duplicated raw text across saves.
    """
    # Read existing local config (may fail if previously corrupted — handled below)
    existing: dict = {}
    if path.exists():
        try:
            with open(path, "rb") as f:
                existing = tomllib.load(f)
        except Exception:
            existing = {}  # treat corrupted file as empty; will be overwritten cleanly

    # Read base config for worker/profile structure
    base_toml_path = path.parent / "cao.config.toml"
    base_cfg: dict = {}
    if base_toml_path.exists():
        try:
            with open(base_toml_path, "rb") as f:
                base_cfg = tomllib.load(f)
        except Exception:
            pass

    # Build merged orchestrator section
    orch = dict(base_cfg.get("orchestrator", {}))
    orch.update(existing.get("orchestrator", {}))
    orch["server_port"] = data["server_port"]
    orch["max_concurrent_workers"] = data["max_concurrent_workers"]

    # Build merged endpoint section
    ep = dict(base_cfg.get("endpoint", {}))
    ep.update(existing.get("endpoint", {}))
    ep["name"] = data["endpoint_name"]
    ep["base_url"] = data["endpoint_url"]
    ep["models"] = models
    ep["default_model"] = data["default_model"]

    # Build merged workers: base first, local overrides on top
    merged_workers: dict = {}
    for wname, wdata in base_cfg.get("workers", {}).items():
        merged_workers[wname] = dict(wdata)
    for wname, wdata in existing.get("workers", {}).items():
        merged_workers.setdefault(wname, {}).update(wdata)

    # Build profiles list
    base_profiles = base_cfg.get("profiles", {}).get("register", [])
    local_profiles = existing.get("profiles", {}).get("register", [])
    register = local_profiles if local_profiles else base_profiles

    # --- Emit clean TOML (no raw-text extraction — prevents duplication) ---
    lines = [
        "# PRIVATE local config — gitignored, overrides cao.config.toml for render/apply.\n",
        "# Your real endpoint + models live here, never in the committed template.\n",
        "\n",
        "[orchestrator]\n",
    ]
    for k, v in orch.items():
        if isinstance(v, bool):
            lines.append(f"{k:<24}= {str(v).lower()}\n")
        elif isinstance(v, str):
            lines.append(f"{k:<24}= {_q(v)}\n")
        else:
            lines.append(f"{k:<24}= {v}\n")
    lines.append("\n")

    lines += [
        "[endpoint]\n",
        f"name     = {_q(ep['name'])}\n",
        f"base_url = {_q(ep['base_url'])}\n",
        "models   = [\n",
    ]
    for m in ep["models"]:
        lines.append(f"  {_q(m)},\n")
    lines += [
        "]\n",
        f"default_model = {_q(ep['default_model'])}\n",
        "\n",
    ]

    # Apply form-submitted coder_worker model override
    coder_model_val = data.get("coder_model", "").strip()
    if coder_model_val and "coder_worker" in merged_workers:
        merged_workers["coder_worker"]["model"] = coder_model_val

    for wname, wdata in merged_workers.items():
        lines.append(f"[workers.{wname}]\n")
        if wdata.get("provider"):
            lines.append(f"provider = {_q(wdata['provider'])}\n")
        if wdata.get("model"):
            lines.append(f"model    = {_q(wdata['model'])}\n")
        aliases = wdata.get("aliases", [])
        if aliases and isinstance(aliases, list):
            lines.append(f"aliases  = [{', '.join(_q(a) for a in aliases)}]\n")
        if wdata.get("focus"):
            lines.append(f"focus    = {_q(wdata['focus'])}\n")
        lines.append("\n")

    if register:
        lines.append("[profiles]\n")
        lines.append("register = [\n")
        for p in register:
            lines.append(f"  {_q(p)},\n")
        lines.append("]\n")

    path.write_text("".join(lines))



def build_workers_table(cfg: dict) -> str:
    workers = cfg.get("workers", {})
    if not workers:
        return "<tr><td colspan='3' style='color:var(--muted)'>No workers found</td></tr>"
    rows = []
    for name, w in workers.items():
        provider = w.get("provider", "—")
        focus = w.get("focus", "")
        # truncate long focus text
        short_focus = focus if len(focus) <= 120 else focus[:117] + "…"
        rows.append(
            f"<tr><td class='worker-name'>{name}</td>"
            f"<td class='provider'>{provider}</td>"
            f"<td class='focus'>{short_focus}</td></tr>"
        )
    return "\n".join(rows)


def build_html(repo: Path) -> str:
    local_toml_path = repo / "2_configure" / "cao.config.local.toml"
    env_path = repo / ".env"

    cfg = read_local_toml(local_toml_path)
    api_key = read_env(env_path)

    orch = cfg.get("orchestrator", {})
    ep = cfg.get("endpoint", {})
    models_list = ep.get("models", [])
    models_str = "\n".join(models_list)
    default_model = ep.get("default_model", "")
    coder_model = cfg.get("workers", {}).get("coder_worker", {}).get("model", "")

    def make_options(models: list[str], selected: str) -> str:
        opts = []
        found = False
        for m in models:
            sel = ' selected' if m == selected else ''
            if m == selected:
                found = True
            opts.append(f'<option value="{m}"{sel}>{m}</option>')
        # If selected value not in list, prepend it so it's preserved
        if selected and not found:
            opts.insert(0, f'<option value="{selected}" selected>{selected} ⚠ not in list</option>')
        return "".join(opts)

    # Mask the API key: show stars if set, empty if not
    api_key_display = "****" + api_key[-4:] if len(api_key) > 4 else ("****" if api_key else "")

    html = HTML
    replacements = {
        "__ENV_PATH__": str(env_path),
        "__LOCAL_TOML_PATH__": str(local_toml_path),
        "__LOCAL_API_KEY__": api_key_display,
        "__ENDPOINT_NAME__": ep.get("name", ""),
        "__BASE_URL__": ep.get("base_url", ""),
        "__MODELS__": models_str,
        "__DEFAULT_MODEL_OPTIONS__": make_options(models_list, default_model),
        "__CODER_MODEL_OPTIONS__": make_options(models_list, coder_model),
        "__SERVER_PORT__": str(orch.get("server_port", 9889)),
        "__MAX_WORKERS__": str(orch.get("max_concurrent_workers", 4)),
        "__WORKERS_TABLE__": build_workers_table(cfg),
    }
    for k, v in replacements.items():
        html = html.replace(k, v)
    return html


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class ConfigHandler(http.server.BaseHTTPRequestHandler):
    repo: Path
    last_activity: list  # mutable reference [float]

    def touch(self):
        self.last_activity[0] = time.time()

    def log_message(self, fmt, *args):  # suppress default Apache-style log
        pass

    def send_json(self, code: int, obj: dict):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.touch()
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            page = build_html(self.repo).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        self.touch()
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/shutdown":
            self.send_json(200, {"ok": True, "message": "Shutting down"})
            # Shut down server in a daemon thread so this response is sent first
            def _stop():
                time.sleep(0.3)
                self.server._shutdown_requested = True
                self.server.shutdown()
            threading.Thread(target=_stop, daemon=True).start()
            return

        if parsed.path == "/save":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
            except json.JSONDecodeError as e:
                self.send_json(400, {"ok": False, "error": str(e)})
                return

            local_toml_path = self.repo / "2_configure" / "cao.config.local.toml"
            env_path = self.repo / ".env"
            apply_sh = self.repo / "3_apply" / "apply.sh"

            # Parse models: one per line or comma-separated
            models_raw = data.get("models", "")
            models = [
                m.strip()
                for line in models_raw.splitlines()
                for m in line.split(",")
                if m.strip()
            ]

            # Write .env (only if api_key field is not the masked placeholder)
            api_key = data.get("local_api_key", "")
            if api_key and not re.match(r'^\*{4}', api_key):
                write_env(env_path, api_key)

            # Write local TOML
            try:
                write_local_toml(local_toml_path, data, models)
            except Exception as e:
                self.send_json(500, {"ok": False, "error": f"TOML write failed: {e}"})
                return

            # Run apply.sh
            output_parts = ["=== Saved config files ===\n"]
            output_parts.append(f"  {local_toml_path}\n")
            output_parts.append(f"  {env_path}\n\n")
            output_parts.append("=== Running ./3_apply/apply.sh ===\n")

            if apply_sh.exists():
                try:
                    result = subprocess.run(
                        [str(apply_sh)],
                        cwd=str(self.repo),
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )
                    output_parts.append(result.stdout)
                    if result.stderr:
                        output_parts.append("\n--- stderr ---\n")
                        output_parts.append(result.stderr)
                    ok = result.returncode == 0
                    if not ok:
                        output_parts.append(f"\n[Exit code: {result.returncode}]\n")
                except subprocess.TimeoutExpired:
                    output_parts.append("\n[apply.sh timed out after 60s]\n")
                    ok = False
            else:
                output_parts.append(f"[Warning: {apply_sh} not found — skipping apply]\n")
                ok = True

            self.send_json(200, {"ok": ok, "output": "".join(output_parts)})
            return

        self.send_response(404)
        self.end_headers()


# ---------------------------------------------------------------------------
# Server + inactivity watchdog
# ---------------------------------------------------------------------------

def make_handler(repo: Path, last_activity: list):
    class Handler(ConfigHandler):
        pass
    Handler.repo = repo
    Handler.last_activity = last_activity
    return Handler


def run(repo: Path):
    last_activity = [time.time()]

    server = http.server.HTTPServer(("127.0.0.1", PORT), make_handler(repo, last_activity))
    server._shutdown_requested = False

    def watchdog():
        while True:
            time.sleep(5)
            if server._shutdown_requested:
                break
            if time.time() - last_activity[0] > INACTIVITY_TIMEOUT:
                print(f"\n[cao-config] No activity for {INACTIVITY_TIMEOUT}s — shutting down.")
                server.shutdown()
                break

    t = threading.Thread(target=watchdog, daemon=True)
    t.start()

    print(f"[cao-config] Config editor running at http://localhost:{PORT}")
    print(f"[cao-config] Press Ctrl-C or click Done to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[cao-config] Stopped.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: cao_config_server.py <repo_root>", file=sys.stderr)
        sys.exit(1)
    repo_root = Path(sys.argv[1]).resolve()
    if not repo_root.is_dir():
        print(f"Error: {repo_root} is not a directory", file=sys.stderr)
        sys.exit(1)
    run(repo_root)
