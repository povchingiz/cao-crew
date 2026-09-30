"""Unit tests for cao-run --sv flag parsing and normalization."""
import subprocess
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
CAO_RUN = REPO / "run" / "cao-run"


class TestCaoRunFlags(unittest.TestCase):
    def _run_bash_eval(self, script: str) -> str:
        cmd = ["bash", "-c", f"source {CAO_RUN.as_posix()} 2>/dev/null; " + script]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return res.stdout.strip()

    def test_normalize_sv_engine_aliases(self):
        cases = {
            "agy": "antigravity_cli",
            "antigravity": "antigravity_cli",
            "gemini": "antigravity_cli",
            "claude": "claude_code",
            "cc": "claude_code",
            "codex": "codex",
            "openai": "codex",
            "opencode": "opencode_cli",
            "oc": "opencode_cli",
            "coder": "opencode_cli",
            "hermes": "hermes_cli",
            "nous": "hermes_cli",
            "copilot": "copilot_cli",
            "gh": "copilot_cli",
            "custom_engine": "custom_engine",
        }
        for alias, expected in cases.items():
            script = f'echo "$(normalize_sv_engine "{alias}")"'
            out = subprocess.run(
                [
                    "bash",
                    "-c",
                    f'eval "$(sed -n \'/^normalize_sv_engine()/,/^}}/p\' {CAO_RUN})"; {script}',
                ],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            self.assertEqual(out, expected, f"Failed for alias: {alias}")

    def test_help_contains_sv_flag(self):
        res = subprocess.run([str(CAO_RUN), "-h"], capture_output=True, text=True, check=True)
        self.assertIn("--sv <engine>", res.stdout)
        self.assertIn("agy, codex, claude, opencode, hermes", res.stdout)


if __name__ == "__main__":
    unittest.main()
