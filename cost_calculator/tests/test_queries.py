import unittest
from unittest.mock import patch

import pandas as pd

from utils import queries


class QueryRoutingTests(unittest.TestCase):
    @patch("utils.queries.pd.read_sql")
    def test_default_costs_read_from_app_database(self, mock_read_sql):
        queries.get_default_costs()

        self.assertIs(mock_read_sql.call_args.args[1], queries.app_cnxn)

    @patch("utils.queries.pd.read_sql")
    def test_last_part_cost_reads_from_app_database(self, mock_read_sql):
        queries.get_last_part_cost("WP100S", "")

        self.assertIs(mock_read_sql.call_args.args[1], queries.app_cnxn)

    @patch("utils.queries.pd.read_sql")
    def test_part_lookup_reads_from_erp_database(self, mock_read_sql):
        queries.get_part("WP100S", "")

        self.assertIs(mock_read_sql.call_args.args[1], queries.erp_cnxn)

    @patch("utils.queries.part_costs_has_current_column", return_value=True)
    @patch("utils.queries.run_app_query")
    def test_recent_costs_use_seek_cursor_instead_of_offset(
        self, mock_run_app_query, _mock_current_column
    ):
        cursor_date = pd.Timestamp("2026-07-13T10:30:00")

        queries.get_recent_part_costs(
            11,
            before_date=cursor_date,
            before_id=321,
            part_id_prefix="WA20",
        )

        query, params = mock_run_app_query.call_args.args
        self.assertIn("SELECT TOP 11", query)
        self.assertIn("ucpPartID LIKE :param1", query)
        self.assertIn("ucpDateCosted < :param2", query)
        self.assertIn("ucpPartCostID < :param3", query)
        self.assertNotIn("OFFSET", query.upper())
        self.assertEqual(params, ("WA20%", cursor_date, 321))

    @patch("utils.queries.part_costs_has_current_column", return_value=True)
    @patch("utils.queries.run_app_query")
    def test_recent_costs_have_bounded_page_size(
        self, mock_run_app_query, _mock_current_column
    ):
        queries.get_recent_part_costs(100000)

        query = mock_run_app_query.call_args.args[0]
        self.assertIn("SELECT TOP 101", query)

    @patch("utils.queries.part_costs_has_current_column", return_value=True)
    @patch("utils.queries.run_app_query")
    def test_recent_costs_can_seek_toward_newer_rows(
        self, mock_run_app_query, _mock_current_column
    ):
        cursor_date = pd.Timestamp("2026-07-07T12:00:00")

        queries.get_recent_part_costs(11, after_date=cursor_date, after_id=20)

        query, params = mock_run_app_query.call_args.args
        self.assertIn("ucpDateCosted > :param1", query)
        self.assertIn("ucpPartCostID > :param2", query)
        self.assertIn("ucpDateCosted ASC", query)
        self.assertEqual(params, (cursor_date, 20))

    @patch("utils.queries.part_costs_has_current_column", return_value=True)
    @patch("utils.queries.run_app_query")
    def test_recent_costs_can_start_at_oldest_edge(
        self, mock_run_app_query, _mock_current_column
    ):
        queries.get_recent_part_costs(11, oldest_first=True)

        query = mock_run_app_query.call_args.args[0]
        self.assertIn("ucpDateCosted ASC", query)
        self.assertNotIn("OFFSET", query.upper())
