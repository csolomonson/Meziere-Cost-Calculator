import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from user_management import UserConflictError, add_user, delete_user, list_users, update_user


class UserManagementTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name, "users.json")
        self.path.write_text(json.dumps({
            "admin": {"password_hash": "existing", "groups": ["users", "administrators"]},
            "operator": {"password_hash": "existing", "groups": ["users"]},
        }))
        self.environment = patch.dict(
            os.environ, {"COST_APP_USERS_JSON_FILE": str(self.path)}, clear=True
        )
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.directory.cleanup()

    def test_listing_never_exposes_credentials(self):
        users = list_users()
        self.assertEqual(users[0], {"username": "admin", "groups": ["users", "administrators"]})
        self.assertNotIn("password_hash", users[0])

    @patch("user_management.password_hash", return_value="new-hash")
    def test_add_and_change_user(self, make_hash):
        add_user("new.user", "long-password", ["users"])
        users = update_user("new.user", "replacement", ["users", "costers"])
        self.assertIn({"username": "new.user", "groups": ["users", "costers"]}, users)
        stored = json.loads(self.path.read_text())
        self.assertEqual(stored["new.user"]["password_hash"], "new-hash")
        self.assertEqual(make_hash.call_count, 2)

    def test_last_administrator_is_protected(self):
        with self.assertRaises(UserConflictError):
            update_user("admin", None, ["users"])
        with self.assertRaises(UserConflictError):
            delete_user("admin")

    def test_non_administrator_can_be_deleted(self):
        users = delete_user("operator")
        self.assertEqual([user["username"] for user in users], ["admin"])


if __name__ == "__main__":
    unittest.main()
