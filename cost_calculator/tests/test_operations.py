import unittest
from unittest.mock import patch

import pandas as pd

from costing import operations
from tests.costing_fixtures import (
    COST_QUANTITY,
    PART_ID,
    REVISION_ID,
    wpbbc01u_defaults_df,
    wpbbc01u_external_po_df,
    wpbbc01u_operations_df,
)


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
        self.assertEqual(external_line["ucoExternalCost"], 8000.00)
        updated = operations.update_internal_costs(lines)
        external_total = updated[updated["ucoPartOperationLineID"] == 40].iloc[0]
        self.assertEqual(external_total["ucoMachineRawCost"], 0.0)
        self.assertEqual(external_total["ucoMachineMarkedUpCost"], 0.0)
        self.assertEqual(external_total["ucoLaborRawCost"], 0.0)
        self.assertEqual(external_total["ucoLaborMarkedUpCost"], 0.0)
        self.assertEqual(external_total["ucoExternalOperationRawCost"], 8000.00)
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

        off = operations.update_internal_costs(
            pd.DataFrame([{**base, "ucoUseAfterHoursIdle": False}])
        ).iloc[0]
        discounted = operations.update_internal_costs(
            pd.DataFrame([{
                **base,
                "ucoUseAfterHoursIdle": True,
                "ucoAfterHoursIdleRateMultiplier": 0.5,
            }])
        ).iloc[0]

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
