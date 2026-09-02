import base64
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from authentication import AuthorizationError, AuthenticationError, Principal, authenticate_request, authorize_costing, password_hash


def request(username: str, password: str):
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return SimpleNamespace(headers={"Authorization": f"Basic {token}"})


class AuthenticationTests(unittest.TestCase):
    def test_costing_group_is_allowed(self):
        authorize_costing(Principal("costing", ("users",)))

    def test_administrators_are_allowed(self):
        authorize_costing(Principal("admin", ("administrators",)))

    def test_sales_order_only_user_is_denied(self):
        with self.assertRaises(AuthorizationError):
            authorize_costing(Principal("shipper", ("sales-orders",)))

    def test_hashed_user_authenticates_with_groups(self):
        users = {
            "alice": {
                "password_hash": password_hash("correct horse", iterations=10),
                "groups": ["costers"],
            }
        }
        with patch.dict(os.environ, {"COST_APP_USERS_JSON": json.dumps(users)}, clear=True):
            principal = authenticate_request(request("alice", "correct horse"))
        self.assertEqual(principal.username, "alice")
        self.assertEqual(principal.groups, ("costers",))

    def test_incorrect_password_is_rejected(self):
        users = {"alice": password_hash("right", iterations=10)}
        with patch.dict(os.environ, {"COST_APP_USERS_JSON": json.dumps(users)}, clear=True):
            with self.assertRaises(AuthenticationError):
                authenticate_request(request("alice", "wrong"))

    def test_successful_hash_verification_is_cached(self):
        users = {"cache-test-user": password_hash("right", iterations=10)}
        environment = {"COST_APP_USERS_JSON": json.dumps(users), "COST_APP_AUTH_CACHE_SECONDS": "300"}
        with patch.dict(os.environ, environment, clear=True), patch(
            "authentication._verify_pbkdf2", wraps=__import__("authentication")._verify_pbkdf2
        ) as verify:
            authenticate_request(request("cache-test-user", "right"))
            authenticate_request(request("cache-test-user", "right"))
        self.assertEqual(verify.call_count, 1)

    def test_development_identity_requires_explicit_opt_out(self):
        environment = {
            "COST_APP_AUTH_REQUIRED": "false",
            "COST_APP_DEV_USERNAME": "local-tester",
        }
        with patch.dict(os.environ, environment, clear=True):
            principal = authenticate_request(SimpleNamespace(headers={}))
        self.assertEqual(principal.username, "local-tester")
        self.assertEqual(principal.groups, ("users",))


if __name__ == "__main__":
    unittest.main()
