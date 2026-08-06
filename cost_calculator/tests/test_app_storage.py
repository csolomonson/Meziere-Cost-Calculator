import unittest
from unittest.mock import patch

from utils import app_storage


class AppStorageTests(unittest.TestCase):
    def test_default_schema_qualifies_app_tables(self):
        with patch.object(app_storage, "APP_SCHEMA", "dbo"):
            self.assertEqual(
                app_storage.app_table("PartCosts"),
                "[dbo].[PartCosts]",
            )
            self.assertEqual(
                app_storage.app_object_name("PartCosts"),
                "dbo.PartCosts",
            )

    def test_erp_namespace_qualifies_app_tables(self):
        with patch.object(app_storage, "APP_SCHEMA", "CostCalculator"):
            self.assertEqual(
                app_storage.app_table("PartCosts"),
                "[CostCalculator].[PartCosts]",
            )
            self.assertEqual(
                app_storage.app_object_name("PartCosts"),
                "CostCalculator.PartCosts",
            )

    def test_unsafe_schema_or_table_identifier_is_rejected(self):
        with patch.object(app_storage, "APP_SCHEMA", "dbo; DROP DATABASE M1_ME"):
            with self.assertRaisesRegex(RuntimeError, "Unsupported SQL identifier"):
                app_storage.app_table("PartCosts")

        with self.assertRaisesRegex(RuntimeError, "Unsupported SQL identifier"):
            app_storage.app_table("PartCosts]")


if __name__ == "__main__":
    unittest.main()
