import unittest
from unittest.mock import Mock, patch

import pandas as pd

from costing import persistence
from tests.costing_fixtures import PART_ID


class PersistenceTests(unittest.TestCase):
    def test_assert_app_database_rejects_non_app_database(self):
        connection = Mock()
        connection.execute.return_value.scalar_one.return_value = "M1_ME"

        with self.assertRaisesRegex(RuntimeError, "Refusing to write costing data to M1_ME"):
            persistence.assert_app_database(connection)

    def test_assert_app_database_allows_m2_me(self):
        connection = Mock()
        connection.execute.return_value.scalar_one.return_value = "M2_ME"

        persistence.assert_app_database(connection)

    def test_frame_for_table_keeps_existing_non_identity_columns_only(self):
        df = pd.DataFrame([
            {
                "ucpPartCostID": 10,
                "ucpPartID": PART_ID,
                "ucpTotalRawCost": 41882.5,
                "draftOnlyColumn": "ignore me",
            }
        ])

        with patch(
            "costing.persistence.get_table_columns",
            return_value={"ucpPartCostID", "ucpPartID", "ucpTotalRawCost"},
        ):
            frame = persistence.frame_for_table(
                connection=Mock(),
                table_name="PartCosts",
                df=df,
            )

        self.assertEqual(list(frame.columns), ["ucpPartID", "ucpTotalRawCost"])

    def test_operation_line_sequence_is_saved_per_part_cost(self):
        df = pd.DataFrame([
            {
                "ucoPartOperationLineID": 10,
                "ucoPartCostID": 101,
                "ucoWorkCenterID": "M22",
                "draftOnlyColumn": "ignore me",
            }
        ])

        with patch(
            "costing.persistence.get_table_columns",
            return_value={"ucoPartOperationLineID", "ucoPartCostID", "ucoWorkCenterID"},
        ):
            frame = persistence.frame_for_table(
                connection=Mock(),
                table_name="OperationCostLines",
                df=df,
            )

        self.assertEqual(
            list(frame.columns),
            ["ucoPartOperationLineID", "ucoPartCostID", "ucoWorkCenterID"],
        )
        self.assertEqual(frame.loc[0, "ucoPartOperationLineID"], 10)

    @patch("costing.persistence.inspect")
    def test_table_metadata_uses_the_configured_schema(self, mock_inspect):
        inspector = mock_inspect.return_value
        inspector.get_columns.return_value = [{"name": "ucpPartID"}]

        self.assertEqual(
            persistence.get_table_columns(Mock(), "PartCosts"),
            {"ucpPartID"},
        )
        inspector.get_columns.assert_called_once_with(
            "PartCosts",
            schema=persistence.APP_SCHEMA,
        )

    def test_clean_row_converts_nan_to_none(self):
        row = persistence.clean_row({"value": float("nan"), "part": PART_ID})

        self.assertIsNone(row["value"])

    def test_clean_row_converts_nat_string_to_none(self):
        row = persistence.clean_row({"date": "NaT", "part": PART_ID})

        self.assertIsNone(row["date"])

    def test_clean_frame_converts_nat_dates_to_none(self):
        frame = persistence.clean_frame(pd.DataFrame([{
            "ucmLastPODate": pd.NaT,
            "ucoLastPODate": "NaT",
            "ucmMaterialID": "WP03C",
        }]))

        self.assertIsNone(frame.loc[0, "ucmLastPODate"])
        self.assertIsNone(frame.loc[0, "ucoLastPODate"])
        self.assertEqual(frame.loc[0, "ucmMaterialID"], "WP03C")
