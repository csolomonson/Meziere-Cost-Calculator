import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from update_contract import request_update, update_status


class UpdateContractTests(unittest.TestCase):
    def test_missing_status_is_offline_without_disrupting_current_version(self):
        environment = {"APP_VERSION": "1.2.3", "UPDATE_STATUS_FILE": "missing-status.json"}
        with patch.dict(os.environ, environment, clear=True):
            status = update_status()
        self.assertEqual(status["status"], "offline")
        self.assertEqual(status["current_version"], "1.2.3")
        self.assertFalse(status["update_available"])

    def test_available_release_creates_attributed_request(self):
        with tempfile.TemporaryDirectory() as directory:
            status_path = Path(directory, "status.json")
            request_path = Path(directory, "request.json")
            status_path.write_text(json.dumps({
                "status": "available",
                "available_version": "2.0.0",
                "update_available": True,
            }))
            environment = {
                "UPDATE_STATUS_FILE": str(status_path),
                "UPDATE_REQUEST_FILE": str(request_path),
            }
            with patch.dict(os.environ, environment, clear=True):
                request_update("alice")
            payload = json.loads(request_path.read_text())
        self.assertEqual(payload["requested_by"], "alice")
        self.assertEqual(payload["requested_version"], "2.0.0")


if __name__ == "__main__":
    unittest.main()
