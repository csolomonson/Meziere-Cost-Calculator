import unittest
from unittest.mock import patch

import pandas as pd

from costing import materials
from tests.costing_fixtures import (
    COST_QUANTITY,
    PART_ID,
    REVISION_ID,
    converted_material_po_df,
    empty_bom_for_children,
    manufactured_part_cost_df,
    wpbbc01u_bom_df,
    wpbbc01u_defaults_df,
    wpbbc01u_material_po_df,
)


class WPBBC01UMaterialTests(unittest.TestCase):
    @patch("costing.materials.get_current_retail_price")
    @patch("costing.materials.get_operations")
    @patch("costing.materials.get_last_part_cost")
    @patch("costing.materials.get_last_material_po")
    @patch("costing.materials.get_default_costs")
    @patch("costing.materials.get_bom")
    def test_wpbbc01u_builds_one_material_line_from_last_po(
        self, mock_bom, mock_defaults, mock_po, mock_history, mock_operations, mock_retail
    ):
        mock_bom.side_effect = empty_bom_for_children
        mock_defaults.return_value = wpbbc01u_defaults_df()
        mock_po.return_value = wpbbc01u_material_po_df()
        mock_history.return_value = pd.DataFrame()
        mock_operations.return_value = pd.DataFrame()
        mock_retail.return_value = pd.DataFrame()

        lines = materials.build_material_cost_lines(
            part_id=PART_ID,
            revision_id=REVISION_ID,
            part_cost_id=1,
            cost_quantity=COST_QUANTITY,
        )

        self.assertEqual(len(lines), 1)
        line = lines.iloc[0]
        self.assertEqual(line["ucmMaterialID"], "WPBBC01U-MAT")
        self.assertTrue(line["ucmIsPurchased"])
        self.assertEqual(line["ucmLastPO"], "PO7001-1")
        self.assertEqual(line["ucmLastPOCost"], 3.10)
        self.assertEqual(line["ucmLastPODate"], pd.Timestamp("2026-06-10"))
        self.assertEqual(line["ucmTotalQuantityRequired"], COST_QUANTITY)
        self.assertEqual(line["ucmMinimumPurchaseQty"], 1.0)
        self.assertEqual(line["ucmRawCost"], 31000.0)
        self.assertEqual(line["ucmMarkedUpCost"], 38750.0)
        mock_po.assert_called_once_with("WPBBC01U-MAT", "")

    @patch("costing.materials.get_current_retail_price")
    @patch("costing.materials.get_operations")
    @patch("costing.materials.get_last_part_cost")
    @patch("costing.materials.get_last_material_po")
    @patch("costing.materials.get_default_costs")
    @patch("costing.materials.get_bom")
    def test_material_po_uses_inventory_unit_cost_after_conversion(
        self, mock_bom, mock_defaults, mock_po, mock_history, mock_operations, mock_retail
    ):
        mock_bom.side_effect = empty_bom_for_children
        mock_defaults.return_value = wpbbc01u_defaults_df()
        mock_po.return_value = converted_material_po_df()
        mock_history.return_value = pd.DataFrame()
        mock_operations.return_value = pd.DataFrame()
        mock_retail.return_value = pd.DataFrame()

        lines = materials.build_material_cost_lines(
            part_id=PART_ID,
            revision_id=REVISION_ID,
            part_cost_id=1,
            cost_quantity=COST_QUANTITY,
        )

        line = lines.iloc[0]
        self.assertEqual(line["ucmUnitCost"], 1.5)
        self.assertEqual(line["ucmLastPOCost"], 1.5)
        self.assertEqual(line["ucmRawCost"], 15000.0)
        self.assertEqual(line["ucmMarkedUpCost"], 18750.0)

    @patch("costing.materials.get_current_retail_price")
    @patch("costing.materials.get_operations")
    @patch("costing.materials.get_last_part_cost")
    @patch("costing.materials.get_last_material_po")
    @patch("costing.materials.get_default_costs")
    @patch("costing.materials.get_bom")
    def test_wpbbc01u_material_falls_back_to_bom_estimate_without_po(
        self, mock_bom, mock_defaults, mock_po, mock_history, mock_operations, mock_retail
    ):
        mock_bom.side_effect = empty_bom_for_children
        mock_defaults.return_value = wpbbc01u_defaults_df()
        mock_po.return_value = pd.DataFrame()
        mock_history.return_value = pd.DataFrame()
        mock_operations.return_value = pd.DataFrame()
        mock_retail.return_value = pd.DataFrame()

        lines = materials.build_material_cost_lines(
            part_id=PART_ID,
            revision_id=REVISION_ID,
            part_cost_id=1,
            cost_quantity=COST_QUANTITY,
        )

        line = lines.iloc[0]
        self.assertFalse(line["ucmIsPurchased"])
        self.assertIsNone(line["ucmLastPO"])
        self.assertEqual(line["ucmUnitCost"], 2.75)
        self.assertEqual(line["ucmRawCost"], 27500.0)
        self.assertEqual(line["ucmMarkedUpCost"], 34375.0)

    @patch("costing.materials.get_current_retail_price")
    @patch("costing.materials.get_operations")
    @patch("costing.materials.get_last_part_cost")
    @patch("costing.materials.get_last_material_po")
    @patch("costing.materials.get_default_costs")
    @patch("costing.materials.get_bom")
    def test_material_with_route_and_po_is_not_treated_as_purchased(
        self, mock_bom, mock_defaults, mock_po, mock_history, mock_operations, mock_retail
    ):
        mock_bom.return_value = wpbbc01u_bom_df()
        mock_defaults.return_value = wpbbc01u_defaults_df()
        mock_po.return_value = wpbbc01u_material_po_df()
        mock_history.return_value = pd.DataFrame()
        mock_operations.return_value = pd.DataFrame()
        mock_retail.return_value = pd.DataFrame()

        lines = materials.build_material_cost_lines(
            part_id=PART_ID,
            revision_id=REVISION_ID,
            part_cost_id=1,
            cost_quantity=COST_QUANTITY,
        )

        line = lines.iloc[0]
        self.assertFalse(line["ucmIsPurchased"])
        self.assertEqual(line["ucmCostSource"], "manufactured_route")
        self.assertEqual(line["ucmMinimumPurchaseQty"], 0.0)
        self.assertEqual(line["ucmUnitCost"], 2.75)

    @patch("costing.materials.get_current_retail_price")
    @patch("costing.materials.get_operations")
    @patch("costing.materials.get_last_part_cost")
    @patch("costing.materials.get_last_material_po")
    @patch("costing.materials.get_default_costs")
    @patch("costing.materials.get_bom")
    def test_manufactured_history_uses_raw_unit_cost_with_parent_markup(
        self, mock_bom, mock_defaults, mock_po, mock_history, mock_operations, mock_retail
    ):
        mock_bom.side_effect = empty_bom_for_children
        mock_defaults.return_value = wpbbc01u_defaults_df()
        mock_po.return_value = pd.DataFrame()
        mock_history.return_value = manufactured_part_cost_df()
        mock_operations.return_value = pd.DataFrame()
        mock_retail.return_value = pd.DataFrame()

        lines = materials.build_material_cost_lines(
            part_id=PART_ID,
            revision_id=REVISION_ID,
            part_cost_id=1,
            cost_quantity=COST_QUANTITY,
        )

        line = lines.iloc[0]
        self.assertEqual(line["ucmCostSource"], "manufactured_history")
        self.assertEqual(line["ucmUnitCost"], 4.0)
        self.assertEqual(line["ucmMaterialMarkup"], 1.25)
        self.assertEqual(line["ucmRawCost"], 40000.0)
        self.assertEqual(line["ucmMarkedUpCost"], 50000.0)

    def test_material_minimum_purchase_quantity_is_manual_purchase_increment(self):
        lines = pd.DataFrame([
            {
                "ucmTotalQuantityRequired": 145.0,
                "ucmIsPurchased": True,
                "ucmMinimumPurchaseQty": 144.0,
                "ucmUnitCost": 2.0,
                "ucmMaterialMarkup": 1.25,
                "ucmWasteQuantity": 0.0,
                "ucmRawCost": 0.0,
                "ucmMarkedUpCost": 0.0,
            }
        ])

        line = materials.update_material_costs(lines).iloc[0]

        self.assertEqual(line["ucmWasteQuantity"], 143.0)
        self.assertEqual(line["ucmRawCost"], 576.0)
        self.assertEqual(line["ucmMarkedUpCost"], 720.0)

    @patch("costing.materials.get_current_retail_price")
    @patch("costing.materials.get_operations")
    @patch("costing.materials.get_last_part_cost")
    @patch("costing.materials.get_last_material_po")
    @patch("costing.materials.get_default_costs")
    @patch("costing.materials.get_bom")
    def test_missing_backflush_is_treated_as_non_backflush_and_zero_cost(
        self, mock_bom, mock_defaults, mock_po, mock_history, mock_operations, mock_retail
    ):
        bom_without_backflush = wpbbc01u_bom_df().drop(columns=["immBackflush"])

        def bom_for_part(part_id, _revision_id=""):
            return bom_without_backflush if part_id == PART_ID else pd.DataFrame()

        mock_bom.side_effect = bom_for_part
        mock_defaults.return_value = wpbbc01u_defaults_df()
        mock_po.return_value = wpbbc01u_material_po_df()
        mock_history.return_value = pd.DataFrame()
        mock_operations.return_value = pd.DataFrame()
        mock_retail.return_value = pd.DataFrame()

        line = materials.build_material_cost_lines(
            part_id=PART_ID,
            revision_id=REVISION_ID,
            part_cost_id=1,
            cost_quantity=COST_QUANTITY,
        ).iloc[0]

        self.assertFalse(line["ucmBackflush"])
        self.assertEqual(line["ucmRawCost"], 0.0)
        self.assertEqual(line["ucmMarkedUpCost"], 0.0)
