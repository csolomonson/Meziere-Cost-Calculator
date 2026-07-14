import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


RUNNER_PATH = (
    Path(__file__).resolve().parents[1] / "deployment" / "windows" / "run_api.py"
)
SPEC = importlib.util.spec_from_file_location("windows_api_runner", RUNNER_PATH)
runner = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(runner)


class WindowsRunnerTests(unittest.TestCase):
    def test_load_environment_normalizes_scalars_and_preserves_explicit_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "settings.json"
            path.write_text(
                json.dumps({"TEXT": "configured", "COUNT": 2, "ENABLED": True}),
                encoding="utf-8",
            )
            environment = {"TEXT": "explicit"}

            runner.load_environment(path, environment)

        self.assertEqual(environment["TEXT"], "explicit")
        self.assertEqual(environment["COUNT"], "2")
        self.assertEqual(environment["ENABLED"], "true")

    def test_load_environment_rejects_structured_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "settings.json"
            path.write_text(json.dumps({"INVALID": ["value"]}), encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "INVALID"):
                runner.load_environment(path, {})

    def test_load_environment_accepts_windows_powershell_utf8_bom(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "settings.json"
            path.write_bytes(b"\xef\xbb\xbf" + json.dumps({"PORT": 8000}).encode())
            environment = {}

            runner.load_environment(path, environment)

        self.assertEqual(environment["PORT"], "8000")

    def test_server_options_are_local_and_validate_bounds(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                runner.server_options(),
                {
                    "host": "127.0.0.1",
                    "port": 8000,
                    "workers": 2,
                    "proxy_headers": True,
                    "forwarded_allow_ips": "127.0.0.1",
                },
            )

        with patch.dict(os.environ, {"COST_APP_PORT": "70000"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "COST_APP_PORT"):
                runner.server_options()


if __name__ == "__main__":
    unittest.main()
