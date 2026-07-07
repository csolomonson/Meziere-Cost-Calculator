import unittest
from unittest.mock import Mock, patch

import pandas as pd

from costing import calculator, materials, operations, persistence
from utils import queries


PART_ID = "WPBBC01U"
REVISION_ID = ""
COST_QUANTITY = 10000


def wpbbc01u_defaults_df():
    return pd.DataFrame([
        {
            "ucdWorkCenterID": "__GLOBAL__",
            "ucdMinimumQuantity": 1,
            "ucdDefaultLaborHourlyCost": 25.0,
            "ucdDefaultMachineRunningHourlyCost": 20.0,
            "ucdDefaultMachineOccupiedHourlyCost": 5.0,
            "ucdDefaultMaterialMarkup": 1.25,
            "ucdDefaultLaborMarkup": 1.15,
            "ucdDefaultMachineCostMarkup": 1.15,
            "ucdDefaultExternalOperationMarkup": 1.25,
            "ucdDefaultAdditionalCostMarkup": 1.15,
        }
    ])


def wpbbc01u_operations_df(include_external=False):
    rows = [
        (10, "SAW1", "CUT01", "Saw Cutting", 0.25, 1.5, 1),
        (20, "M22", "MILL", "MILL OPERATION", 8.75, 34.6667, 1),
        (30, "WETHE", "DEBUR", "Parts Deburring", 1.0, 20.0, 1),
        (40, "POLIS", "POLIS", "Polishing", 0.1, 10.0, 1),
        (50, "DRYHE", "POLIS", "Polishing", 0.1, 15.0, 1),
        (60, "WASH", "WASH", "Parts Washing", 0.25, 0.25, 1),
    ]

    if include_external:
        rows[3] = (40, "POLIS", "POLIS", "Polishing", 0.1, 10.0, 2)

    return pd.DataFrame([
        {
            "imoMethodID": PART_ID,
            "imoMethodRevisionID": REVISION_ID,
            "imoMethodOperationID": method_operation_id,
            "imoWorkCenterID": work_center_id,
            "imoProcessID": process_id,
            "imoProcessShortDescription": description,
            "imoQuantityPerAssembly": 1.0,
            "imoSetupHours": setup_hours,
            "imoProductionStandard": production_standard_minutes,
            "imoOperationType": operation_type,
        }
        for (
            method_operation_id,
            work_center_id,
            process_id,
            description,
            setup_hours,
            production_standard_minutes,
            operation_type,
        ) in rows
    ])


def wpbbc01u_bom_df():
    return pd.DataFrame([
        {
            "immMethodID": PART_ID,
            "immMethodRevisionID": REVISION_ID,
            "immPartID": "WPBBC01U-MAT",
            "immPartRevisionID": "",
            "immPartShortDescription": "WPBBC01U raw material",
            "immQuantityPerAssembly": 1.0,
            "immEstimatedUnitCost": 2.75,
        }
    ])


def empty_bom_for_children(part_id, revision_id=""):
    return wpbbc01u_bom_df() if part_id == PART_ID else pd.DataFrame()


def wpbbc01u_part_df():
    return pd.DataFrame([
        {
            "impPartID": PART_ID,
            "impPartRevisionID": REVISION_ID,
            "impPartShortDescription": "WPBBC01U finished part",
        }
    ])


def wpbbc01u_material_po_df():
    return pd.DataFrame([
        {
            "pmlPurchaseOrderID": "PO7001",
            "pmlPurchaseOrderLineID": 1,
            "pmlPurchaseUnitCostBase": 3.10,
            "pmlPurchaseQuantity": 12000,
            "pmlPurchaseQuantityReceived": 12000,
            "pmlDueDate": pd.NaT,
            "pmlCreatedDate": pd.Timestamp("2026-06-10"),
        }
    ])


def wpbbc01u_external_po_df():
    return pd.DataFrame([
        {
            "pmlPurchaseOrderID": "PO9001",
            "pmlPurchaseOrderLineID": 3,
            "pmlPurchaseUnitCostBase": 0.80,
            "pmlSetupChargeBase": 125.00,
            "pmlTotalExtendedCostBase": 8125.00,
            "pmlPurchaseQuantity": 10000,
            "pmlPurchaseQuantityReceived": 10000,
            "pmlDueDate": pd.NaT,
            "pmlCreatedDate": pd.Timestamp("2026-06-15"),
        }
    ])


class WPBBC01UOperationTests(unittest.TestCase):
    @patch("costing.operations.get_last_external_operation_po")
    @patch("costing.operations.get_default_costs")
    @patch("costing.operations.get_operations")
    def test_wpbbc01u_builds_six_operations_at_expected_locations(
        self, mock_ops, mock_defaults, mock_po
    ):
        mock_ops.return_value = wpbbc01u_operations_df()
        mock_defaults.return_value = wpbbc01u_defaults_df()
        mock_po.return_value = pd.DataFrame()

        lines = operations.build_operation_cost_lines(
            part_id=PART_ID,
            revision_id=REVISION_ID,
            part_cost_id=1,
            cost_quantity=COST_QUANTITY,
        )

        self.assertEqual(len(lines), 6)
        self.assertEqual(
            lines["ucoWorkCenterID"].tolist(),
            ["SAW1", "M22", "WETHE", "POLIS", "DRYHE", "WASH"],
        )
        self.assertEqual(lines["ucoPartOperationLineID"].tolist(), [10, 20, 30, 40, 50, 60])
        self.assertAlmostEqual(lines.loc[0, "ucoCycleTimeHours"], 0.025)
        self.assertAlmostEqual(lines.loc[1, "ucoCycleTimeHours"], 0.5777783333333333)
        mock_po.assert_not_called()

    @patch("costing.operations.get_last_external_operation_po")
    @patch("costing.operations.get_default_costs")
    @patch("costing.operations.get_operations")
    def test_wpbbc01u_external_operation_uses_matching_job_operation_po(
        self, mock_ops, mock_defaults, mock_po
    ):
        mock_ops.return_value = wpbbc01u_operations_df(include_external=True)
        mock_defaults.return_value = wpbbc01u_defaults_df()
        mock_po.return_value = wpbbc01u_external_po_df()

        lines = operations.build_operation_cost_lines(
            part_id=PART_ID,
            revision_id=REVISION_ID,
            part_cost_id=1,
            cost_quantity=COST_QUANTITY,
        )

        external_line = lines[lines["ucoPartOperationLineID"] == 40].iloc[0]
        self.assertTrue(external_line["ucoExternalJob"])
        self.assertEqual(external_line["ucoLastPO"], "PO9001-3")
        self.assertEqual(external_line["ucoLastPOCost"], 0.80)
        self.assertEqual(external_line["ucoLastPODate"], pd.Timestamp("2026-06-15"))
        self.assertEqual(external_line["ucoExternalCost"], 8125.00)
        updated = operations.update_internal_costs(lines)
        external_total = updated[updated["ucoPartOperationLineID"] == 40].iloc[0]
        self.assertEqual(external_total["ucoMachineRawCost"], 0.0)
        self.assertEqual(external_total["ucoMachineMarkedUpCost"], 0.0)
        self.assertEqual(external_total["ucoLaborRawCost"], 0.0)
        self.assertEqual(external_total["ucoLaborMarkedUpCost"], 0.0)
        self.assertEqual(external_total["ucoExternalOperationRawCost"], 8125.00)
        mock_po.assert_called_once_with(
            part_id=PART_ID,
            revision_id=REVISION_ID,
            method_operation_id=40,
        )

    def test_external_operation_zeros_machine_and_labor_even_with_internal_inputs(self):
        lines = pd.DataFrame([
            {
                "ucoExternalJob": True,
                "ucoCostQuantity": 10,
                "ucoQuantityPerAssembly": 1,
                "ucoBatchSize": 1,
                "ucoAdditionalCostPerPart": 0.0,
                "ucoAdditionalCostTotal": 0.0,
                "ucoAdditionalCostMarkup": 1.0,
                "ucoSetupLaborRate": 25.0,
                "ucoSetupTimeHours": 5.0,
                "ucoBatchResetLaborRate": 25.0,
                "ucoBatchResetTimeHours": 1.0,
                "ucoLaborMarkup": 1.15,
                "ucoCycleTimeHours": 2.0,
                "ucoBatchIdleTimeHours": 0.0,
                "ucoMachineOccupiedHourlyCost": 5.0,
                "ucoMachineRunningHourlyCost": 20.0,
                "ucoMachineCostMarkup": 1.15,
                "ucoExternalCost": 500.0,
                "ucoExternalOperationMarkup": 1.25,
            }
        ])

        result = operations.update_internal_costs(lines).iloc[0]

        self.assertEqual(result["ucoMachineRawCost"], 0.0)
        self.assertEqual(result["ucoMachineMarkedUpCost"], 0.0)
        self.assertEqual(result["ucoLaborRawCost"], 0.0)
        self.assertEqual(result["ucoLaborMarkedUpCost"], 0.0)
        self.assertEqual(result["ucoExternalOperationRawCost"], 500.0)
        self.assertEqual(result["ucoExternalOperationMarkedUpCost"], 625.0)
        self.assertEqual(result["ucoLineRawCost"], 500.0)
        self.assertEqual(result["ucoLineMarkedUpCost"], 625.0)

    def test_after_hours_idle_time_rounds_to_next_first_shift_start(self):
        lines = pd.DataFrame([
            {
                "ucoExternalJob": False,
                "ucoCostQuantity": 10,
                "ucoQuantityPerAssembly": 1,
                "ucoBatchSize": 1,
                "ucoAdditionalCostPerPart": 0.0,
                "ucoAdditionalCostTotal": 0.0,
                "ucoAdditionalCostMarkup": 1.0,
                "ucoSetupLaborRate": 0.0,
                "ucoSetupTimeHours": 0.0,
                "ucoBatchResetLaborRate": 0.0,
                "ucoBatchResetTimeHours": 0.0,
                "ucoBatchIdleTimeHours": 0.0,
                "ucoLaborMarkup": 1.0,
                "ucoCycleTimeHours": 0.2,
                "ucoMachineOccupiedHourlyCost": 5.0,
                "ucoMachineRunningHourlyCost": 20.0,
                "ucoMachineCostMarkup": 1.0,
                "ucoExternalCost": 0.0,
                "ucoExternalOperationMarkup": 1.0,
                "ucoUseAfterHoursIdle": True,
                "ucoStartTime": "13:30",
                "ucoAfterHoursIdleRateMultiplier": 1.0,
                "ucoFirstShiftStartTime": "06:00",
                "ucoFirstShiftEndTime": "14:30",
            }
        ])

        result = operations.update_internal_costs(lines).iloc[0]

        self.assertEqual(result["ucoAfterHoursIdleTimeHours"], 14.5)
        self.assertEqual(result["ucoMachineRawCost"], 122.5)

    def test_after_hours_idle_time_is_zero_when_operation_finishes_before_shift_end(self):
        lines = pd.DataFrame([
            {
                "ucoExternalJob": False,
                "ucoCostQuantity": 10,
                "ucoQuantityPerAssembly": 1,
                "ucoBatchSize": 1,
                "ucoAdditionalCostPerPart": 0.0,
                "ucoAdditionalCostTotal": 0.0,
                "ucoAdditionalCostMarkup": 1.0,
                "ucoSetupLaborRate": 0.0,
                "ucoSetupTimeHours": 0.0,
                "ucoBatchResetLaborRate": 0.0,
                "ucoBatchResetTimeHours": 0.0,
                "ucoBatchIdleTimeHours": 0.0,
                "ucoLaborMarkup": 1.0,
                "ucoCycleTimeHours": 0.1,
                "ucoMachineOccupiedHourlyCost": 5.0,
                "ucoMachineRunningHourlyCost": 20.0,
                "ucoMachineCostMarkup": 1.0,
                "ucoExternalCost": 0.0,
                "ucoExternalOperationMarkup": 1.0,
                "ucoUseAfterHoursIdle": True,
                "ucoStartTime": "13:00",
                "ucoAfterHoursIdleRateMultiplier": 1.0,
                "ucoFirstShiftStartTime": "06:00",
                "ucoFirstShiftEndTime": "14:30",
            }
        ])

        result = operations.update_internal_costs(lines).iloc[0]

        self.assertEqual(result["ucoAfterHoursIdleTimeHours"], 0.0)
        self.assertEqual(result["ucoMachineRawCost"], 25.0)

    def test_after_hours_idle_time_handles_multi_day_finish_after_hours(self):
        lines = pd.DataFrame([
            {
                "ucoExternalJob": False,
                "ucoCostQuantity": 1,
                "ucoQuantityPerAssembly": 1,
                "ucoBatchSize": 1,
                "ucoAdditionalCostPerPart": 0.0,
                "ucoAdditionalCostTotal": 0.0,
                "ucoAdditionalCostMarkup": 1.0,
                "ucoSetupLaborRate": 0.0,
                "ucoSetupTimeHours": 0.0,
                "ucoBatchResetLaborRate": 0.0,
                "ucoBatchResetTimeHours": 0.0,
                "ucoBatchIdleTimeHours": 0.0,
                "ucoLaborMarkup": 1.0,
                "ucoCycleTimeHours": 26.0,
                "ucoMachineOccupiedHourlyCost": 5.0,
                "ucoMachineRunningHourlyCost": 20.0,
                "ucoMachineCostMarkup": 1.0,
                "ucoExternalCost": 0.0,
                "ucoExternalOperationMarkup": 1.0,
                "ucoUseAfterHoursIdle": True,
                "ucoStartTime": "13:30",
                "ucoAfterHoursIdleRateMultiplier": 1.0,
                "ucoFirstShiftStartTime": "06:00",
                "ucoFirstShiftEndTime": "14:30",
            }
        ])

        result = operations.update_internal_costs(lines).iloc[0]

        self.assertEqual(result["ucoAfterHoursIdleTimeHours"], 14.5)
        self.assertEqual(result["ucoMachineRawCost"], 722.5)

    def test_after_hours_idle_time_is_optional_and_discountable(self):
        base = {
            "ucoExternalJob": False,
            "ucoCostQuantity": 10,
            "ucoQuantityPerAssembly": 1,
            "ucoBatchSize": 1,
            "ucoAdditionalCostPerPart": 0.0,
            "ucoAdditionalCostTotal": 0.0,
            "ucoAdditionalCostMarkup": 1.0,
            "ucoSetupLaborRate": 0.0,
            "ucoSetupTimeHours": 0.0,
            "ucoBatchResetLaborRate": 0.0,
            "ucoBatchResetTimeHours": 0.0,
            "ucoBatchIdleTimeHours": 0.0,
            "ucoLaborMarkup": 1.0,
            "ucoCycleTimeHours": 0.2,
            "ucoMachineOccupiedHourlyCost": 5.0,
            "ucoMachineRunningHourlyCost": 20.0,
            "ucoMachineCostMarkup": 1.0,
            "ucoExternalCost": 0.0,
            "ucoExternalOperationMarkup": 1.0,
            "ucoStartTime": "13:30",
            "ucoFirstShiftStartTime": "06:00",
            "ucoFirstShiftEndTime": "14:30",
        }

        off = operations.update_internal_costs(pd.DataFrame([{**base, "ucoUseAfterHoursIdle": False}])).iloc[0]
        discounted = operations.update_internal_costs(pd.DataFrame([{**base, "ucoUseAfterHoursIdle": True, "ucoAfterHoursIdleRateMultiplier": 0.5}])).iloc[0]

        self.assertEqual(off["ucoAfterHoursIdleTimeHours"], 0.0)
        self.assertEqual(off["ucoMachineRawCost"], 50.0)
        self.assertEqual(discounted["ucoAfterHoursIdleTimeHours"], 14.5)
        self.assertEqual(discounted["ucoMachineRawCost"], 86.25)

    def test_wpbbc01u_operation_totals_match_known_route_math(self):
        lines = pd.DataFrame([
            {
                "ucoCostQuantity": COST_QUANTITY,
                "ucoQuantityPerAssembly": 1.0,
                "ucoBatchSize": 1,
                "ucoAdditionalCostPerPart": 0.0,
                "ucoAdditionalCostTotal": 0.0,
                "ucoAdditionalCostMarkup": 1.15,
                "ucoSetupLaborRate": 25.0,
                "ucoSetupTimeHours": 0.25,
                "ucoBatchResetLaborRate": 25.0,
                "ucoBatchResetTimeHours": 0.0,
                "ucoLaborMarkup": 1.15,
                "ucoCycleTimeHours": 0.025,
                "ucoBatchIdleTimeHours": 0.0,
                "ucoMachineOccupiedHourlyCost": 5.0,
                "ucoMachineRunningHourlyCost": 20.0,
                "ucoMachineCostMarkup": 1.15,
                "ucoExternalCost": 0.0,
                "ucoExternalOperationMarkup": 1.25,
            }
        ])

        result = operations.update_internal_costs(lines).iloc[0]

        self.assertAlmostEqual(result["ucoMachineRawCost"], 6251.25)
        self.assertAlmostEqual(result["ucoMachineMarkedUpCost"], 7188.9375)
        self.assertAlmostEqual(result["ucoLaborRawCost"], 6.25)
        self.assertAlmostEqual(result["ucoLaborMarkedUpCost"], 7.1875)
        self.assertAlmostEqual(result["ucoLineRawCost"], 6257.5)
        self.assertAlmostEqual(result["ucoLineMarkedUpCost"], 7196.125)


class WPBBC01UMaterialTests(unittest.TestCase):
    @patch("costing.materials.get_operations")
    @patch("costing.materials.get_last_part_cost")
    @patch("costing.materials.get_last_material_po")
    @patch("costing.materials.get_default_costs")
    @patch("costing.materials.get_bom")
    def test_wpbbc01u_builds_one_material_line_from_last_po(
        self, mock_bom, mock_defaults, mock_po, mock_history, mock_operations
    ):
        mock_bom.side_effect = empty_bom_for_children
        mock_defaults.return_value = wpbbc01u_defaults_df()
        mock_po.return_value = wpbbc01u_material_po_df()
        mock_history.return_value = pd.DataFrame()
        mock_operations.return_value = pd.DataFrame()

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

    @patch("costing.materials.get_operations")
    @patch("costing.materials.get_last_part_cost")
    @patch("costing.materials.get_last_material_po")
    @patch("costing.materials.get_default_costs")
    @patch("costing.materials.get_bom")
    def test_wpbbc01u_material_falls_back_to_bom_estimate_without_po(
        self, mock_bom, mock_defaults, mock_po, mock_history, mock_operations
    ):
        mock_bom.side_effect = empty_bom_for_children
        mock_defaults.return_value = wpbbc01u_defaults_df()
        mock_po.return_value = pd.DataFrame()
        mock_history.return_value = pd.DataFrame()
        mock_operations.return_value = pd.DataFrame()

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

    @patch("costing.materials.get_operations")
    @patch("costing.materials.get_last_part_cost")
    @patch("costing.materials.get_last_material_po")
    @patch("costing.materials.get_default_costs")
    @patch("costing.materials.get_bom")
    def test_material_with_route_and_po_is_not_treated_as_purchased(
        self, mock_bom, mock_defaults, mock_po, mock_history, mock_operations
    ):
        mock_bom.return_value = wpbbc01u_bom_df()
        mock_defaults.return_value = wpbbc01u_defaults_df()
        mock_po.return_value = wpbbc01u_material_po_df()
        mock_history.return_value = pd.DataFrame()
        mock_operations.return_value = pd.DataFrame()

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


class WPBBC01UCostRunTests(unittest.TestCase):
    @patch("costing.calculator.get_part")
    @patch("costing.calculator.build_material_cost_lines")
    @patch("costing.calculator.build_operation_cost_lines")
    def test_wpbbc01u_full_cost_run_summarizes_operations_and_one_material(
        self, mock_operation_lines, mock_material_lines, mock_part
    ):
        operation_lines = operations.update_internal_costs(
            pd.DataFrame([
                {
                    "ucoCostQuantity": COST_QUANTITY,
                    "ucoQuantityPerAssembly": 1.0,
                    "ucoBatchSize": 1,
                    "ucoAdditionalCostPerPart": 0.0,
                    "ucoAdditionalCostTotal": 0.0,
                    "ucoAdditionalCostMarkup": 1.15,
                    "ucoSetupLaborRate": 25.0,
                    "ucoSetupTimeHours": 0.25,
                    "ucoBatchResetLaborRate": 25.0,
                    "ucoBatchResetTimeHours": 0.0,
                    "ucoLaborMarkup": 1.15,
                    "ucoCycleTimeHours": 0.025,
                    "ucoBatchIdleTimeHours": 0.0,
                    "ucoMachineOccupiedHourlyCost": 5.0,
                    "ucoMachineRunningHourlyCost": 20.0,
                    "ucoMachineCostMarkup": 1.15,
                    "ucoExternalCost": 0.0,
                    "ucoExternalOperationMarkup": 1.25,
                },
                {
                    "ucoCostQuantity": COST_QUANTITY,
                    "ucoQuantityPerAssembly": 1.0,
                    "ucoBatchSize": 1,
                    "ucoAdditionalCostPerPart": 0.0,
                    "ucoAdditionalCostTotal": 0.0,
                    "ucoAdditionalCostMarkup": 1.15,
                    "ucoSetupLaborRate": 25.0,
                    "ucoSetupTimeHours": 0.0,
                    "ucoBatchResetLaborRate": 25.0,
                    "ucoBatchResetTimeHours": 0.0,
                    "ucoLaborMarkup": 1.15,
                    "ucoCycleTimeHours": 0.0,
                    "ucoBatchIdleTimeHours": 0.0,
                    "ucoMachineOccupiedHourlyCost": 0.0,
                    "ucoMachineRunningHourlyCost": 0.0,
                    "ucoMachineCostMarkup": 1.15,
                    "ucoExternalCost": 8125.0,
                    "ucoExternalOperationMarkup": 1.25,
                },
            ])
        )
        material_lines = pd.DataFrame([
            {
                "ucmTotalQuantityRequired": COST_QUANTITY,
                "ucmMinimumPurchaseQty": 0.0,
                "ucmUnitCost": 2.75,
                "ucmMaterialMarkup": 1.25,
                "ucmRawCost": 0.0,
                "ucmMarkedUpCost": 0.0,
            }
        ])
        mock_part.return_value = wpbbc01u_part_df()
        mock_operation_lines.return_value = operation_lines
        mock_material_lines.return_value = material_lines

        result = calculator.build_part_cost(
            part_id=PART_ID,
            revision_id=REVISION_ID,
            cost_quantity=COST_QUANTITY,
            costed_by="test",
        )

        summary = result["part_cost"].iloc[0]
        self.assertEqual(summary["ucpPartID"], PART_ID)
        self.assertEqual(len(result["material_lines"]), 1)
        self.assertAlmostEqual(summary["ucpMaterialsRawCost"], 27500.0)
        self.assertAlmostEqual(summary["ucpMachineTimeRawCost"], 6251.25)
        self.assertAlmostEqual(summary["ucpLaborRawCost"], 6.25)
        self.assertAlmostEqual(summary["ucpExternalOperationsRawCost"], 8125.0)
        self.assertAlmostEqual(summary["ucpTotalRawCost"], 41882.5)
        self.assertAlmostEqual(summary["ucpUnitRawCost"], 4.18825)


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


if __name__ == "__main__":
    unittest.main()
