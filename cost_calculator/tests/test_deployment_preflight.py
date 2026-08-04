import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tools import deployment_preflight


class DeploymentPreflightTests(unittest.TestCase):
    def test_user_check_prefers_the_persisted_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            users_path = Path(temporary) / "app_users.json"
            users_path.write_text(
                json.dumps(
                    {
                        "admin": {
                            "password_hash": "hash",
                            "groups": ["users", "administrators"],
                        }
                    }
                ),
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {"COST_APP_USERS_JSON_FILE": str(users_path)},
                clear=False,
            ):
                deployment_preflight.check_user_seed()

    def test_erp_check_requires_access_to_the_parts_table(self):
        engine = MagicMock()
        connection = engine.connect.return_value.__enter__.return_value

        with patch.object(deployment_preflight, "erp_cnxn", engine):
            deployment_preflight.check_erp_database()

        query = str(connection.execute.call_args.args[0])
        self.assertIn("FROM Parts", query)

    def test_costing_check_lists_a_missing_required_table(self):
        engine = MagicMock()
        connection = engine.connect.return_value.__enter__.return_value

        def execute(_query, parameters):
            result = MagicMock()
            result.scalar_one.return_value = parameters["table_name"] != "dbo.MarkupBreaks"
            return result

        connection.execute.side_effect = execute
        with patch.object(deployment_preflight, "app_cnxn", engine):
            with self.assertRaisesRegex(RuntimeError, "MarkupBreaks"):
                deployment_preflight.check_costing_database()


if __name__ == "__main__":
    unittest.main()
