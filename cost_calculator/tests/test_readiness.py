import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from web.routers import system


def engine_with_connection():
    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value
    connection.execute.return_value = 1
    return engine


class ReadinessTests(unittest.TestCase):
    def test_readiness_checks_both_databases(self):
        erp = engine_with_connection()
        costing = engine_with_connection()

        with patch.object(system, "erp_cnxn", erp), patch.object(system, "app_cnxn", costing):
            result = system.readiness()

        self.assertEqual(result, {"ok": True, "databases": ["erp", "costing"]})
        erp.connect.return_value.__enter__.return_value.execute.assert_called_once()
        costing.connect.return_value.__enter__.return_value.execute.assert_called_once()

    def test_readiness_is_unavailable_when_a_database_cannot_connect(self):
        erp = engine_with_connection()
        costing = engine_with_connection()
        costing.connect.return_value.__enter__.side_effect = RuntimeError("offline")

        with patch.object(system, "erp_cnxn", erp), patch.object(system, "app_cnxn", costing):
            with self.assertRaises(HTTPException) as raised:
                system.readiness()

        self.assertEqual(raised.exception.status_code, 503)
        self.assertNotIn("offline", raised.exception.detail)


if __name__ == "__main__":
    unittest.main()
